"""
Email service for Satisfy application
Supports SendGrid, AWS SES, and SMTP fallback
"""
import os
from typing import Optional

# Email configuration
EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'mock')  # 'sendgrid', 'smtp', or 'mock'
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@satisfy.com')
FROM_NAME = os.environ.get('FROM_NAME', 'Satisfy Platform')

# SMTP settings (fallback)
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> dict:
    """
    Send email using configured provider
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML version of email body
    
    Returns:
        dict with 'success' (bool) and 'message' (str)
    """
    
    if EMAIL_PROVIDER == 'sendgrid':
        return _send_via_sendgrid(to_email, subject, body, html_body)
    elif EMAIL_PROVIDER == 'smtp':
        return _send_via_smtp(to_email, subject, body, html_body)
    else:
        # Mock mode - just print to console
        return _send_mock(to_email, subject, body)

def _send_via_sendgrid(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> dict:
    """Send email via SendGrid API"""
    if not SENDGRID_API_KEY:
        return {
            'success': False,
            'message': 'SendGrid API key not configured. Set SENDGRID_API_KEY environment variable.'
        }
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Content
        
        # Create email message
        message = Mail(
            from_email=(FROM_EMAIL, FROM_NAME),
            to_emails=to_email,
            subject=subject
        )
        
        # Add plain text content
        message.add_content(Content("text/plain", body))
        
        # Add HTML content if provided
        if html_body:
            message.add_content(Content("text/html", html_body))
        
        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        return {
            'success': True,
            'message': f'Email sent successfully via SendGrid (Status: {response.status_code})',
            'status_code': response.status_code
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'SendGrid error: {str(e)}'
        }

def _send_via_smtp(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> dict:
    """Send email via SMTP (Gmail, etc)"""
    if not SMTP_USER or not SMTP_PASSWORD:
        return {
            'success': False,
            'message': 'SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD.'
        }
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'{FROM_NAME} <{FROM_EMAIL}>'
        msg['To'] = to_email
        
        # Add plain text part
        msg.attach(MIMEText(body, 'plain'))
        
        # Add HTML part if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        # Connect to SMTP server and send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        return {
            'success': True,
            'message': f'Email sent successfully via SMTP to {to_email}'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'SMTP error: {str(e)}'
        }

def _send_mock(to_email: str, subject: str, body: str) -> dict:
    """Mock email sending - just print to console"""
    print("\n" + "="*60)
    print("📧 EMAIL SENT (Mock Mode)")
    print("="*60)
    print(f"To: {to_email}")
    print(f"From: {FROM_NAME} <{FROM_EMAIL}>")
    print(f"Subject: {subject}")
    print("-"*60)
    print(body)
    print("="*60 + "\n")
    
    return {
        'success': True,
        'message': 'Email logged to console (mock mode)',
        'preview': body
    }

# Email templates
def get_vendor_approval_email(vendor_name: str, contact_person: str) -> tuple:
    """Generate vendor approval email"""
    subject = "✅ Vendor Application Approved - Satisfy Platform"
    
    body = f"""Dear {contact_person},

Congratulations! Your vendor application for {vendor_name} has been APPROVED.

You can now access the Satisfy Vendor Portal to manage your products and view customer feedback.

🔗 Vendor Portal: http://localhost:5000/vendor

What you can do now:
✓ Add and manage your product listings
✓ View customer likes and dislikes
✓ Track product performance
✓ Update product information anytime

If you have any questions, please contact our support team.

Best regards,
The Satisfy Team

---
This is an automated message from Satisfy Platform."""
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f7f7f7;">
            <div style="background: #00704A; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">☕ Satisfy</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2 style="color: #00704A;">✅ Vendor Application Approved!</h2>
                <p>Dear <strong>{contact_person}</strong>,</p>
                <p>Congratulations! Your vendor application for <strong>{vendor_name}</strong> has been APPROVED.</p>
                
                <div style="background: #e8f5e9; padding: 15px; border-left: 4px solid #4caf50; margin: 20px 0;">
                    <p style="margin: 0;"><strong>🔗 Access your portal:</strong></p>
                    <p style="margin: 5px 0;"><a href="http://localhost:5000/vendor" style="color: #00704A;">http://localhost:5000/vendor</a></p>
                </div>
                
                <h3>What you can do now:</h3>
                <ul>
                    <li>✓ Add and manage your product listings</li>
                    <li>✓ View customer likes and dislikes</li>
                    <li>✓ Track product performance</li>
                    <li>✓ Update product information anytime</li>
                </ul>
                
                <p>If you have any questions, please contact our support team.</p>
                
                <p>Best regards,<br><strong>The Satisfy Team</strong></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">This is an automated message from Satisfy Platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, body, html_body

def get_vendor_rejection_email(vendor_name: str, contact_person: str, reason: str) -> tuple:
    """Generate vendor rejection email"""
    subject = "Vendor Application Status - Satisfy Platform"
    
    body = f"""Dear {contact_person},

Thank you for your interest in joining Satisfy with {vendor_name}.

After careful review, we regret to inform you that we cannot approve your application at this time.

Reason: {reason}

If you have any questions or would like to discuss this decision, please contact our support team.

Best regards,
The Satisfy Team

---
This is an automated message from Satisfy Platform."""
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f7f7f7;">
            <div style="background: #00704A; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">☕ Satisfy</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2>Vendor Application Status</h2>
                <p>Dear <strong>{contact_person}</strong>,</p>
                <p>Thank you for your interest in joining Satisfy with <strong>{vendor_name}</strong>.</p>
                <p>After careful review, we regret to inform you that we cannot approve your application at this time.</p>
                
                <div style="background: #ffebee; padding: 15px; border-left: 4px solid #f44336; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Reason:</strong> {reason}</p>
                </div>
                
                <p>If you have any questions or would like to discuss this decision, please contact our support team.</p>
                
                <p>Best regards,<br><strong>The Satisfy Team</strong></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">This is an automated message from Satisfy Platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, body, html_body

def get_vendor_blocked_email(vendor_name: str, contact_person: str, reason: str) -> tuple:
    """Generate vendor blocked notification email"""
    subject = "🚫 Account Blocked - Satisfy Platform"
    
    body = f"""Dear {contact_person},

Your vendor account for {vendor_name} has been blocked by an administrator.

Reason: {reason}

Your vendor portal access has been suspended. Please contact support for more information.

Best regards,
The Satisfy Admin Team

---
This is an automated message from Satisfy Platform."""
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f7f7f7;">
            <div style="background: #d32f2f; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">☕ Satisfy</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2 style="color: #d32f2f;">🚫 Account Blocked</h2>
                <p>Dear <strong>{contact_person}</strong>,</p>
                <p>Your vendor account for <strong>{vendor_name}</strong> has been blocked by an administrator.</p>
                
                <div style="background: #ffebee; padding: 15px; border-left: 4px solid #d32f2f; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Reason:</strong> {reason}</p>
                </div>
                
                <p>Your vendor portal access has been suspended. Please contact support for more information.</p>
                
                <p>Best regards,<br><strong>The Satisfy Admin Team</strong></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">This is an automated message from Satisfy Platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, body, html_body

def get_vendor_suspended_email(vendor_name: str, contact_person: str, reason: str) -> tuple:
    """Generate vendor suspension notification email"""
    subject = "⏸️ Account Suspended - Satisfy Platform"
    
    body = f"""Dear {contact_person},

Your vendor account for {vendor_name} has been temporarily suspended.

Reason: {reason}

Your vendor portal access is paused. Please resolve the issue to restore access.
This is a temporary measure and can be resolved.

If you have any questions, please contact support.

Best regards,
The Satisfy Admin Team

---
This is an automated message from Satisfy Platform."""
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f7f7f7;">
            <div style="background: #ff9800; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">☕ Satisfy</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2 style="color: #ff9800;">⏸️ Account Suspended</h2>
                <p>Dear <strong>{contact_person}</strong>,</p>
                <p>Your vendor account for <strong>{vendor_name}</strong> has been temporarily suspended.</p>
                
                <div style="background: #fff3e0; padding: 15px; border-left: 4px solid #ff9800; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Reason:</strong> {reason}</p>
                </div>
                
                <p>Your vendor portal access is paused. Please resolve the issue to restore access.</p>
                <p><em>This is a temporary measure and can be resolved.</em></p>
                
                <p>If you have any questions, please contact support.</p>
                
                <p>Best regards,<br><strong>The Satisfy Admin Team</strong></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">This is an automated message from Satisfy Platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, body, html_body

def get_vendor_restored_email(vendor_name: str, contact_person: str) -> tuple:
    """Generate vendor account restored email"""
    subject = "✅ Account Restored - Satisfy Platform"
    
    body = f"""Dear {contact_person},

Good news! Your vendor account for {vendor_name} has been restored.

Your vendor portal access is now active again. You can continue managing your products.

Thank you for resolving the issue.

🔗 Vendor Portal: http://localhost:5000/vendor

Best regards,
The Satisfy Admin Team

---
This is an automated message from Satisfy Platform."""
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f7f7f7;">
            <div style="background: #4caf50; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">☕ Satisfy</h1>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                <h2 style="color: #4caf50;">✅ Account Restored</h2>
                <p>Dear <strong>{contact_person}</strong>,</p>
                <p>Good news! Your vendor account for <strong>{vendor_name}</strong> has been restored.</p>
                
                <div style="background: #e8f5e9; padding: 15px; border-left: 4px solid #4caf50; margin: 20px 0;">
                    <p style="margin: 0;">Your vendor portal access is now active again.</p>
                    <p style="margin: 5px 0;"><a href="http://localhost:5000/vendor" style="color: #00704A;">Access Vendor Portal</a></p>
                </div>
                
                <p>Thank you for resolving the issue.</p>
                
                <p>Best regards,<br><strong>The Satisfy Admin Team</strong></p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">This is an automated message from Satisfy Platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, body, html_body
