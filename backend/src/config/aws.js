const AWS = require('aws-sdk');

AWS.config.update({
  region: process.env.AWS_REGION || 'us-east-1',
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
});

const s3 = new AWS.S3({
  signatureVersion: 'v4'
});

const rekognition = new AWS.Rekognition();

const sqs = new AWS.SQS();

const cloudwatch = new AWS.CloudWatch();

module.exports = {
  s3,
  rekognition,
  sqs,
  cloudwatch
};
