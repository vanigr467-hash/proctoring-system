import * as tf from "@tensorflow/tfjs";

let model = null;

export async function loadPhoneModel() {
  if (!model) {
    model = await tf.loadGraphModel(
      "https://storage.googleapis.com/tfjs-models/savedmodel/ssdlite_mobilenet_v2/model.json"
    );
  }
  return model;
}

export async function detectPhone(video) {
  if (!model) return false;

  const input = tf.browser.fromPixels(video).expandDims(0).toFloat();
  const predictions = await model.executeAsync(input);

  const boxes = predictions[1].arraySync();
  const classes = predictions[3].arraySync();

  // COCO class 77 = "cell phone"
  for (let i = 0; i < classes[0].length; i++) {
    if (classes[0][i] === 77) {
      return true;
    }
  }
  return false;
}
