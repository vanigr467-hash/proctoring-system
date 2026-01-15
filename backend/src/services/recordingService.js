const { s3 } = require('../config/aws');
const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');
const ffmpeg = require('fluent-ffmpeg');
const stream = require('stream');

class RecordingService {
  constructor() {
    this.activeRecordings = new Map();
  }

  async startRecording(sessionId, studentId) {
    const recordingId = uuidv4();
    const key = `recordings/${sessionId}/${studentId}/${recordingId}.webm`;
    
    this.activeRecordings.set(`${sessionId}-${studentId}`, {
      recordingId,
      key,
      chunks: [],
      startTime: Date.now()
    });

    logger.info(`Started recording for student ${studentId} in session ${sessionId}`);
    return recordingId;
  }

  async addChunk(sessionId, studentId, chunk) {
    const recordingKey = `${sessionId}-${studentId}`;
    const recording = this.activeRecordings.get(recordingKey);
    
    if (!recording) {
      throw new Error('No active recording found');
    }

    recording.chunks.push(chunk);

    // Upload chunk to S3 every 10 chunks to prevent memory overflow
    if (recording.chunks.length >= 10) {
      await this.flushChunks(sessionId, studentId);
    }
  }

  async flushChunks(sessionId, studentId) {
    const recordingKey = `${sessionId}-${studentId}`;
    const recording = this.activeRecordings.get(recordingKey);
    
    if (!recording || recording.chunks.length === 0) {
      return;
    }

    try {
      const buffer = Buffer.concat(recording.chunks);
      const chunkKey = `${recording.key}-chunk-${Date.now()}.webm`;

      await s3.putObject({
        Bucket: process.env.S3_BUCKET_NAME,
        Key: chunkKey,
        Body: buffer,
        ContentType: 'video/webm'
      }).promise();

      recording.chunks = [];
      logger.info(`Flushed recording chunks for ${studentId}`);
    } catch (error) {
      logger.error('Error flushing chunks:', error);
      throw error;
    }
  }

  async stopRecording(sessionId, studentId) {
    const recordingKey = `${sessionId}-${studentId}`;
    const recording = this.activeRecordings.get(recordingKey);
    
    if (!recording) {
      throw new Error('No active recording found');
    }

    // Flush remaining chunks
    await this.flushChunks(sessionId, studentId);

    const url = `https://${process.env.S3_BUCKET_NAME}.s3.amazonaws.com/${recording.key}`;
    
    this.activeRecordings.delete(recordingKey);
    
    logger.info(`Stopped recording for student ${studentId} in session ${sessionId}`);
    
    return {
      recordingId: recording.recordingId,
      url,
      duration: Date.now() - recording.startTime
    };
  }

  async saveScreenshot(sessionId, studentId, imageBuffer) {
    try {
      const key = `screenshots/${sessionId}/${studentId}/${uuidv4()}.jpg`;
      
      await s3.putObject({
        Bucket: process.env.S3_BUCKET_NAME,
        Key: key,
        Body: imageBuffer,
        ContentType: 'image/jpeg'
      }).promise();

      return `https://${process.env.S3_BUCKET_NAME}.s3.amazonaws.com/${key}`;
    } catch (error) {
      logger.error('Error saving screenshot:', error);
      throw error;
    }
  }

  async getRecordingUrl(key, expiresIn = 3600) {
    try {
      const url = await s3.getSignedUrlPromise('getObject', {
        Bucket: process.env.S3_BUCKET_NAME,
        Key: key,
        Expires: expiresIn
      });
      return url;
    } catch (error) {
      logger.error('Error generating signed URL:', error);
      throw error;
    }
  }
}

module.exports = new RecordingService();
