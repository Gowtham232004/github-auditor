"""
email_service.py
Send analysis reports via Gmail SMTP
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from datetime import datetime

# Gmail SMTP Configuration
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

def generate_email_html(username: str, analysis_data: Dict) -> str:
    """
    Generate HTML email template for analysis report
    """
    
    score = analysis_data.get('authenticity_score', 0)
    red_flags = analysis_data.get('red_flags', [])
    profile = analysis_data.get('profile', {})
    
    # Determine score color
    if score >= 80:
        score_color = '#10b981'
        score_label = 'Authentic'
    elif score >= 50:
        score_color = '#f59e0b'
        score_label = 'Questionable'
    else:
        score_color = '#ef4444'
        score_label = 'Suspicious'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; }}
            .score-badge {{ text-align: center; margin: 30px 0; }}
            .score-circle {{ width: 150px; height: 150px; border-radius: 50%; background: {score_color}; color: white; display: inline-flex; align-items: center; justify-content: center; font-size: 48px; font-weight: bold; }}
            .score-label {{ margin-top: 10px; font-size: 24px; font-weight: bold; color: {score_color}; }}
            .section {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .red-flag {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 12px; margin: 10px 0; border-radius: 4px; }}
            .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1> GitHub Profile Analysis Report</h1>
                <p>Analysis for: <strong>@{username}</strong></p>
                <p style="font-size: 14px; opacity: 0.9;">{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
            
            <div class="content">
                <div class="score-badge">
                    <div class="score-circle">{score}</div>
                    <div class="score-label">{score_label}</div>
                    <p style="color: #6b7280;">Authenticity Score (out of 100)</p>
                </div>
                
                <div class="section">
                    <h2> Profile Summary</h2>
                    <p><strong>Username:</strong> {profile.get('username', username)}</p>
                    <p><strong>Name:</strong> {profile.get('name', 'N/A')}</p>
                    <p><strong>Public Repos:</strong> {profile.get('public_repos', 0)}</p>
                    <p><strong>Followers:</strong> {profile.get('followers', 0)}</p>
                    <p><strong>Account Created:</strong> {profile.get('created_at', 'N/A')}</p>
                </div>
                
                <div class="section">
                    <h2> Red Flags Detected ({len(red_flags)})</h2>
                    {''.join([f'<div class="red-flag"><strong>{flag["type"].replace("_", " ").title()}:</strong> {flag["message"]}</div>' for flag in red_flags]) if red_flags else '<p style="color: #10b981;"> No red flags detected! This profile shows healthy development patterns.</p>'}
                </div>
                
                <div class="section">
                    <h2> Recommendation</h2>
                    <p>
                        {
                            " This profile appears authentic and shows consistent development patterns. Safe to proceed with interview process." if score >= 80
                            else " This profile shows some concerns. Recommend additional technical verification during interview." if score >= 50
                            else " This profile shows significant red flags. Careful review and in-depth technical assessment strongly recommended."
                        }
                    </p>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://your-vercel-url.vercel.app/results/{username}" class="button">
                        View Full Report Online
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p>Generated by <strong>GitHub Auditor</strong></p>
                <p>AI-powered profile authenticity analysis</p>
                <p style="font-size: 12px; margin-top: 20px;">
                    This is an automated report. Results should be used as one factor in candidate evaluation.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def send_analysis_email(to_email: str, username: str, analysis_data: Dict) -> bool:
    """
    Send analysis report via Gmail SMTP
    
    Args:
        to_email: Recipient email address
        username: GitHub username analyzed
        analysis_data: Complete analysis data
    
    Returns:
        True if sent successfully, False otherwise
    """
    
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print(" Gmail SMTP not configured - Running in DEMO mode")
        print(f" [DEMO] Would send email to: {to_email}")
        print(f" [DEMO] For user: {username}")
        return True  # Return True in demo mode
    
    try:
        # Generate HTML content
        html_content = generate_email_html(username, analysis_data)
        
        # Create email message
        message = MIMEMultipart('alternative')
        message['Subject'] = f'GitHub Analysis Report: @{username}'
        message['From'] = GMAIL_USER
        message['To'] = to_email
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        message.attach(html_part)
        
        # Connect to Gmail SMTP server
        print(f" Connecting to Gmail SMTP...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            
            # Login
            print(f" Logging in...")
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            
            # Send email
            print(f" Sending email to {to_email}...")
            server.send_message(message)
            
        print(f" Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f" Failed to send email: {str(e)}")
        return False


if __name__ == "__main__":
    # Test the email service
    print("Testing Gmail SMTP Email Service...")
    
    test_data = {
        'authenticity_score': 85,
        'profile': {
            'username': 'test_user',
            'name': 'Test User',
            'public_repos': 50,
            'followers': 100,
            'created_at': '2020-01-01'
        },
        'red_flags': []
    }
    
    result = send_analysis_email('test@example.com', 'test_user', test_data)
    print(f"Test result: {'Success' if result else 'Failed'}")
