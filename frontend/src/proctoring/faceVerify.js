import * as faceapi from "face-api.js";

let modelsLoaded = false;

async function loadModels() {
  if (modelsLoaded) return;

  await faceapi.nets.tinyFaceDetector.load("/models/");
  await faceapi.nets.faceRecognitionNet.load("/models/");
  await faceapi.nets.faceLandmark68Net.load("/models/");
  modelsLoaded = true;
}

export default async function verifyFaceMatch(videoElement, referenceImageUrl) {
  await loadModels();

  // Capture webcam frame
  const detection = await faceapi
    .detectSingleFace(videoElement, new faceapi.TinyFaceDetectorOptions())
    .withFaceLandmarks()
    .withFaceDescriptor();

  if (!detection) {
    return { match: false, confidence: 0 };
  }

  // Load reference image
  const referenceImage = await faceapi.fetchImage(referenceImageUrl);
  const refDetection = await faceapi
    .detectSingleFace(referenceImage, new faceapi.TinyFaceDetectorOptions())
    .withFaceLandmarks()
    .withFaceDescriptor();

  if (!refDetection) {
    return { match: false, confidence: 0 };
  }

  // Compare faces using Euclidean distance
  const distance = faceapi.euclideanDistance(
    detection.descriptor,
    refDetection.descriptor
  );

  const confidence = (1 - distance) * 100;

  return {
    match: distance < 0.5, // threshold
    confidence: confidence.toFixed(2)
  };
}
