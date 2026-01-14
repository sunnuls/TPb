import fs from 'fs';
import path from 'path';
import { pool } from './connection';
import { logger } from '../utils/logger';

async function runMigrations() {
  const migrationsDir = path.join(__dirname, 'migrations');
  const files = fs.readdirSync(migrationsDir).sort();

  logger.info('Starting database migrations...');

  for (const file of files) {
    if (file.endsWith('.sql')) {
      const filePath = path.join(migrationsDir, file);
      const sql = fs.readFileSync(filePath, 'utf-8');

      try {
        logger.info(`Running migration: ${file}`);
        await pool.query(sql);
        logger.info(`✅ Completed migration: ${file}`);
      } catch (error) {
        logger.error(`❌ Failed migration: ${file}`, error);
        throw error;
      }
    }
  }

  logger.info('All migrations completed successfully');
}

// Run if called directly
if (require.main === module) {
  runMigrations()
    .then(() => {
      logger.info('Migration script completed');
      process.exit(0);
    })
    .catch((error) => {
      logger.error('Migration script failed:', error);
      process.exit(1);
    });
}

export { runMigrations };

