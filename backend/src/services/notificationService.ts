import { EventEmitter } from 'events';
import { logger } from '../utils/logger';

export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success' | 'strategy' | 'alert';
  title: string;
  message: string;
  timestamp: Date;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  category: 'game' | 'strategy' | 'system' | 'error' | 'player' | 'equity' | 'warning' | 'achievement';
  data?: any;
  read: boolean;
  dismissed: boolean;
  actionRequired?: boolean;
}

export interface AlertRule {
  id: string;
  name: string;
  enabled: boolean;
  condition: (context: any) => boolean;
  notification: {
    type: Notification['type'];
    title: string;
    message: string;
    priority: Notification['priority'];
  };
}

export interface NotificationConfig {
  enableSound: boolean;
  enableDesktopNotifications: boolean;
  maxNotifications: number;
  autoExpire: boolean;
  expireAfterMs: number;
}

export class NotificationService extends EventEmitter {
  private notifications: Notification[] = [];
  private alertRules: AlertRule[] = [];
  private config: NotificationConfig;

  constructor(config?: Partial<NotificationConfig>) {
    super();
    this.config = {
      enableSound: true,
      enableDesktopNotifications: false,
      maxNotifications: 100,
      autoExpire: true,
      expireAfterMs: 300000, // 5 minutes
      ...config,
    };

    // Setup default alert rules
    this.setupDefaultAlerts();
  }

  /**
   * Send notification
   */
  send(notification: Omit<Notification, 'id' | 'timestamp' | 'read' | 'dismissed'>): Notification {
    const fullNotification: Notification = {
      ...notification,
      id: this.generateId(),
      timestamp: new Date(),
      read: false,
      dismissed: false,
    };

    this.notifications.push(fullNotification);
    this.trimNotifications();

    // Emit event for real-time delivery
    this.emit('notification', fullNotification);

    // Play sound if enabled
    if (this.config.enableSound && fullNotification.priority === 'urgent') {
      this.playAlertSound();
    }

    // Show desktop notification if enabled
    if (this.config.enableDesktopNotifications) {
      this.showDesktopNotification(fullNotification);
    }

    logger.info(`Notification [${fullNotification.priority}]: ${notification.title}`);
    return fullNotification;
  }

  /**
   * Send strategy alert
   */
  sendStrategyAlert(
    title: string,
    message: string,
    priority: Notification['priority'] = 'medium',
    data?: any
  ): void {
    this.send({
      type: 'info',
      title,
      message,
      priority,
      category: 'strategy',
      data,
    });
  }

  /**
   * Send equity alert
   */
  sendEquityAlert(
    title: string,
    message: string,
    equity: number,
    priority: Notification['priority'] = 'medium'
  ): void {
    this.send({
      type: 'info',
      title,
      message,
      priority,
      category: 'equity',
      data: { equity },
    });
  }

  /**
   * Send warning
   */
  sendWarning(title: string, message: string, data?: any): void {
    this.send({
      type: 'warning',
      title,
      message,
      priority: 'high',
      category: 'warning',
      data,
    });
  }

  /**
   * Send error notification
   */
  sendError(title: string, message: string, error?: Error): void {
    this.send({
      type: 'error',
      title,
      message,
      priority: 'high',
      data: { error: error?.message },
    });
  }

  /**
   * Send achievement notification
   */
  sendAchievement(title: string, message: string, data?: any): void {
    this.send({
      type: 'success',
      title,
      message,
      priority: 'low',
      category: 'achievement',
      data,
    });
  }

  /**
   * Send player alert
   */
  sendPlayerAlert(
    playerName: string,
    alert: string,
    priority: Notification['priority'] = 'medium'
  ): Notification {
    return this.send({
      type: 'alert',
      title: `Player: ${playerName}`,
      message: alert,
      priority,
      category: 'player',
    });
  }

  /**
   * Add custom alert rule
   */
  addAlertRule(rule: Omit<AlertRule, 'id'>): AlertRule {
    const fullRule: AlertRule = {
      ...rule,
      id: this.generateId(),
    };

    this.alertRules.push(fullRule);
    logger.info(`Alert rule added: ${fullRule.name}`);

    return fullRule;
  }

  /**
   * Evaluate alert rules
   */
  evaluateAlerts(context: any): void {
    for (const rule of this.alertRules) {
      if (!rule.enabled) continue;

      try {
        if (rule.condition(context)) {
          this.send({
            type: rule.notification.type,
            title: rule.notification.title,
            message: rule.notification.message,
            priority: rule.notification.priority,
            category: 'strategy',
            data: { rule: rule.name, context },
          });
        }
      } catch (error) {
        logger.error(`Alert rule evaluation failed: ${rule.name}`, error);
      }
    }
  }

  /**
   * Setup default alert rules
   */
  private setupDefaultAlerts(): void {
    // Alert when pot is large
    this.addAlertRule({
      name: 'Large Pot',
      enabled: true,
      condition: (ctx) => ctx.pot > 100,
      notification: {
        type: 'alert',
        title: 'Large Pot',
        message: 'Pot size is significant - play carefully',
        priority: 'medium',
      },
    });

    // Alert when facing all-in
    this.addAlertRule({
      name: 'Facing All-In',
      enabled: true,
      condition: (ctx) => ctx.facingAllIn === true,
      notification: {
        type: 'alert',
        title: 'All-In Decision',
        message: 'Facing an all-in - consider pot odds carefully',
        priority: 'urgent',
      },
    });

    // Alert when equity is close
    this.addAlertRule({
      name: 'Close Equity',
      enabled: true,
      condition: (ctx) => ctx.equity && Math.abs(ctx.equity - 0.5) < 0.05,
      notification: {
        type: 'strategy',
        title: 'Close Equity',
        message: 'Equity is close to 50% - marginal decision',
        priority: 'high',
      },
    });
  }

  /**
   * Get all notifications
   */
  getAll(): Notification[] {
    // Auto-expire old notifications if enabled
    if (this.config.autoExpire) {
      this.expireOldNotifications();
    }
    return [...this.notifications];
  }

  /**
   * Get unread notifications
   */
  getUnread(): Notification[] {
    return this.notifications.filter(n => !n.read);
  }

  /**
   * Get notifications by type
   */
  getByType(type: Notification['type']): Notification[] {
    return this.notifications.filter(n => n.type === type);
  }

  /**
   * Get notifications by category
   */
  getByCategory(category: Notification['category']): Notification[] {
    return this.notifications.filter(n => n.category === category);
  }

  /**
   * Get notifications by priority
   */
  getByPriority(priority: Notification['priority']): Notification[] {
    return this.notifications.filter(n => n.priority === priority);
  }

  /**
   * Clear all notifications
   */
  clear(): void {
    this.notifications = [];
    this.emit('cleared');
    logger.info('All notifications cleared');
  }

  /**
   * Clear notifications by type
   */
  clearByType(type: Notification['type']): void {
    this.notifications = this.notifications.filter(n => n.type !== type);
    this.emit('cleared', { type });
  }

  /**
   * Mark notification as read
   */
  markAsRead(id: string): void {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.read = true;
      this.emit('read', notification);
    }
  }

  /**
   * Mark all as read
   */
  markAllAsRead(): void {
    this.notifications.forEach(n => (n.read = true));
    logger.info('All notifications marked as read');
  }

  /**
   * Dismiss notification
   */
  dismissNotification(id: string): void {
    const notification = this.notifications.find(n => n.id === id);
    if (notification) {
      notification.dismissed = true;
      this.emit('dismissed', notification);
    }
  }

  /**
   * Clear dismissed notifications
   */
  clearDismissed(): void {
    this.notifications = this.notifications.filter(n => !n.dismissed);
    logger.info('Dismissed notifications cleared');
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Trim notification history
   */
  private trimNotifications(): void {
    if (this.notifications.length > this.config.maxNotifications) {
      this.notifications = this.notifications.slice(-this.config.maxNotifications);
    }
  }

  /**
   * Expire old notifications
   */
  private expireOldNotifications(): void {
    const now = Date.now();
    const expireThreshold = now - this.config.expireAfterMs;

    this.notifications = this.notifications.filter(
      n => n.timestamp.getTime() > expireThreshold || !n.read
    );
  }

  /**
   * Play alert sound
   */
  private playAlertSound(): void {
    // Placeholder - in production: play system sound
    logger.debug('Alert sound triggered');
  }

  /**
   * Show desktop notification
   */
  private showDesktopNotification(notification: Notification): void {
    // Placeholder - in production: use node-notifier
    logger.debug('Desktop notification triggered', notification.title);
  }

  /**
   * Get alert rules
   */
  getAlertRules(): AlertRule[] {
    return [...this.alertRules];
  }

  /**
   * Toggle alert rule
   */
  toggleAlertRule(id: string, enabled: boolean): void {
    const rule = this.alertRules.find(r => r.id === id);
    if (rule) {
      rule.enabled = enabled;
      logger.info(`Alert rule ${enabled ? 'enabled' : 'disabled'}: ${rule.name}`);
    }
  }

  /**
   * Remove alert rule
   */
  removeAlertRule(id: string): void {
    this.alertRules = this.alertRules.filter(r => r.id !== id);
    logger.info(`Alert rule removed: ${id}`);
  }

  /**
   * Get configuration
   */
  getConfig(): NotificationConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<NotificationConfig>): void {
    this.config = { ...this.config, ...config };
    logger.info('Notification config updated', this.config);
  }
}

