import { Router, Request, Response } from 'express';
import { HandHistoryParser } from '../parsers/handHistoryParser';
import multer from 'multer';

const router = Router();
const parser = new HandHistoryParser();

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
});

/**
 * Parse hand history from text
 */
router.post('/parse', (req: Request, res: Response) => {
  try {
    const { text } = req.body;

    if (!text) {
      res.status(400).json({
        success: false,
        error: { message: 'Missing hand history text', code: 'MISSING_TEXT' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const parsed = parser.parseHandHistory(text);

    res.json({
      success: true,
      data: parsed,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to parse hand history',
        code: 'PARSE_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Parse hand history from uploaded file
 */
router.post('/parse/file', upload.single('file'), (req: Request, res: Response) => {
  try {
    if (!req.file) {
      res.status(400).json({
        success: false,
        error: { message: 'No file uploaded', code: 'NO_FILE' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const text = req.file.buffer.toString('utf-8');
    const hands = parser.parseMultipleHands(text);

    res.json({
      success: true,
      data: {
        totalHands: hands.length,
        hands: hands.slice(0, 100), // Return first 100 hands
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to parse file',
        code: 'PARSE_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

/**
 * Parse multiple hands from text
 */
router.post('/parse/multiple', (req: Request, res: Response) => {
  try {
    const { text } = req.body;

    if (!text) {
      res.status(400).json({
        success: false,
        error: { message: 'Missing hand history text', code: 'MISSING_TEXT' },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    const hands = parser.parseMultipleHands(text);

    res.json({
      success: true,
      data: {
        totalHands: hands.length,
        hands,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Failed to parse hands',
        code: 'PARSE_ERROR',
      },
      timestamp: new Date().toISOString(),
    });
  }
});

export default router;

