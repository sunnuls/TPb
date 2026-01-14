import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { logger } from '../utils/logger';

interface JWTPayload {
  userId: string;
  username: string;
}

declare global {
  namespace Express {
    interface Request {
      user?: JWTPayload;
    }
  }
}

/**
 * JWT Authentication Middleware
 */
export function authenticateToken(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    res.status(401).json({
      success: false,
      error: {
        message: 'Access token required',
        code: 'NO_TOKEN',
      },
      timestamp: new Date().toISOString(),
    });
    return;
  }

  const secret = process.env.JWT_SECRET || 'your_jwt_secret';

  jwt.verify(token, secret, (err, payload) => {
    if (err) {
      logger.warn(`Invalid token: ${err.message}`);
      res.status(403).json({
        success: false,
        error: {
          message: 'Invalid or expired token',
          code: 'INVALID_TOKEN',
        },
        timestamp: new Date().toISOString(),
      });
      return;
    }

    req.user = payload as JWTPayload;
    next();
  });
}

/**
 * Generate JWT token
 */
export function generateToken(userId: string, username: string): string {
  const secret = process.env.JWT_SECRET || 'your_jwt_secret';
  const expiration = process.env.JWT_EXPIRATION || '24h';

  return jwt.sign({ userId, username }, secret, { expiresIn: expiration });
}

/**
 * Optional authentication (doesn't fail if no token)
 */
export function optionalAuth(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    next();
    return;
  }

  const secret = process.env.JWT_SECRET || 'your_jwt_secret';

  jwt.verify(token, secret, (err, payload) => {
    if (!err) {
      req.user = payload as JWTPayload;
    }
    next();
  });
}

