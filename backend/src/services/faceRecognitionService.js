const { rekognition, s3 } = require('../config/aws');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');

class FaceRecognitionService {
  async verifyFace(studentImageBuffer, referenceImageUrl) {
    try {
      // Upload current image to S3
      const key = `face-verification/${uuidv4()}.jpg`;
      await s3.putObject({
        Bucket: process.env.S3_BUCKET_NAME,
        Key: key,
        Body: studentImageBuffer,
        ContentType: 'image/jpeg'
      }).promise();

      // Compare faces using AWS Rekognition
      const params = {
        SourceImage: {
          S3Object: {
            Bucket: process.env.S3_BUCKET_NAME,
            Name: key
          }
        },
        TargetImage: {
          S3Object: {
            Bucket: process.env.S3_BUCKET_NAME,
            Name: this.extractS3Key(referenceImageUrl)
          }
        },
        SimilarityThreshold: 90
      };

      const result = await rekognition.compareFaces(params).promise();
      
      if (result.FaceMatches.length > 0) {
        const similarity = result.FaceMatches[0].Similarity;
        logger.info(`Face match found with ${similarity}% similarity`);
        return {
          verified: true,
          confidence: similarity,
          imageUrl: `https://${process.env.S3_BUCKET_NAME}.s3.amazonaws.com/${key}`
        };
      }

      return {
        verified: false,
        confidence: 0,
        imageUrl: `https://${process.env.S3_BUCKET_NAME}.s3.amazonaws.com/${key}`
      };
    } catch (error) {
      logger.error('Face verification error:', error);
      throw error;
    }
  }

  async detectFaces(imageBuffer) {
    try {
      const params = {
        Image: {
          Bytes: imageBuffer
        },
        Attributes: ['ALL']
      };

      const result = await rekognition.detectFaces(params).promise();
      return {
        faceCount: result.FaceDetails.length,
        faces: result.FaceDetails.map(face => ({
          confidence: face.Confidence,
          emotions: face.Emotions,
          eyeglasses: face.Eyeglasses.Value,
          eyesOpen: face.EyesOpen.Value,
          mouthOpen: face.MouthOpen.Value,
          pose: face.Pose
        }))
      };
    } catch (error) {
      logger.error('Face detection error:', error);
      throw error;
    }
  }

  extractS3Key(url) {
    const urlParts = url.split('.com/');
    return urlParts[1];
  }
}

module.exports = new FaceRecognitionService();
