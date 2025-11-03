"""
email_service.py
Send analysis reports via Resend API (works on Render!)
"""

import os
import resend
from typing import Dict
from datetime import datetime

# Resend API Configuration
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'onboarding@resend.dev')

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

def generate_email_html(username: str, analysis_data: Dict) -> str:
    """Generate HTML email template for analysis report"""
    
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
            .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 10px 0; border-radius: 4px; }}
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
                    {''.join([f'<div class="red-flag"><strong>{flag.get("type", "Unknown")}</strong>: {flag.get("message", "No description")}</div>' for flag in red_flags]) if red_flags else '<p style="color: #10b981;"> No red flags detected! This profile looks authentic.</p>'}
                </div>
                
                <div class="section">
                    <h2> Recommendation</h2>
                    <p>
                        {'This profile shows strong authenticity indicators. Suitable for consideration.' if score >= 80
                         else 'This profile has some concerns. Additional verification recommended.' if score >= 50
                         else 'This profile shows significant red flags. Exercise caution.'}
                    </p>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://github-auditor-frontend-git-main-gowtham-m-ss-projects.vercel.app/results/{username}" class="button">
                        View Full Report Online
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p>This report was generated by GitHub Auditor</p>
                <p style="font-size: 12px; color: #9ca3af;">Automated analysis  Not a substitute for human judgment</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_analysis_email(to_email: str, username: str, analysis_data: Dict) -> bool:
    """
    Send analysis report via Resend API
    
    Note: Resend requires domain verification to send to external emails.
    - For testing: Uses delivered@resend.dev (Resend's test inbox)
    - For production: Verify your domain at https://resend.com/domains
    
    Args:
        to_email: Recipient email address
        username: GitHub username analyzed
        analysis_data: Analysis results dictionary
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    # Demo mode if Resend not configured
    if not RESEND_API_KEY:
        print(" Resend API not configured - Running in DEMO mode")
        print(f" [DEMO] Would send email to: {to_email}")
        print(f" [DEMO] For user: {username}")
        print(f" [DEMO] Set RESEND_API_KEY environment variable to enable email")
        return True
    
    try:
        # Determine recipient based on domain verification
        recipient = to_email
        domain_warning = False
        
        # Check if email domain is likely unverified
        common_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']
        email_domain = to_email.split('@')[-1].lower() if '@' in to_email else ''
        
        if email_domain in common_domains:
            print(f" Domain '{email_domain}' is not verified in Resend")
            print(f" Original recipient: {to_email}")
            print(f" Redirecting to test email: delivered@resend.dev")
            print(f" To send to real emails, verify your domain at: https://resend.com/domains")
            recipient = "delivered@resend.dev"
            domain_warning = True
        
        # Generate HTML content
        html_content = generate_email_html(username, analysis_data)
        
        # Add warning to email if using test address
        if domain_warning:
            warning_html = f'''
            <div class="warning" style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 10px 0; border-radius: 4px;">
                <strong> Test Mode:</strong> This email was requested for <strong>{to_email}</strong> but sent to a test address because the domain is not verified.
                <br><br>
                <strong>To enable real emails:</strong> Verify your domain at <a href="https://resend.com/domains">https://resend.com/domains</a>
            </div>
            '''
            html_content = html_content.replace('</head>', f'{warning_html}</head>')
        
        # Send email via Resend
        print(f" Sending email via Resend API to {recipient}...")
        
        params = {
            "from": FROM_EMAIL,
            "to": [recipient],
            "subject": f"GitHub Analysis Report: @{username}" + (" [TEST MODE]" if domain_warning else ""),
            "html": html_content,
        }
        
        email = resend.Emails.send(params)
        
        print(f" Email sent successfully!")
        print(f"   Email ID: {email.get('id', 'unknown')}")
        print(f"   Sent to: {recipient}")
        
        if domain_warning:
            print(f"    Note: User requested {to_email}, but sent to test address")
            print(f"    Verify your domain to send to real email addresses")
        
        return True
        
    except Exception as e:
        print(f" Failed to send email: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Provide helpful error messages
        if "domain is not verified" in str(e).lower():
            print(f"    Solution: Verify your domain at https://resend.com/domains")
            print(f"    Or: Email will be sent to delivered@resend.dev for testing")
        
        return False

if __name__ == "__main__":
    # Test the email service
    print(" Testing Resend Email Service...\n")
    
    test_data = {
        'authenticity_score': 87,
        'red_flags': [
            {'type': 'irregular_commits', 'message': 'Commits concentrated in specific hours'},
        ],
        'profile': {
            'username': 'testuser',
            'name': 'Test User',
            'public_repos': 42,
            'followers': 123,
            'created_at': '2020-01-15'
        }
    }
    
    # Test with a Gmail address (will redirect to test email)
    print("=" * 60)
    print("Test 1: Sending to Gmail address (should redirect to test)")
    print("=" * 60)
    success1 = send_analysis_email('test@gmail.com', 'testuser', test_data)
    print(f"\n Test 1 Result: {' Success' if success1 else ' Failed'}\n")
    
    print("=" * 60)
    print("Test 2: Sending to test address directly")
    print("=" * 60)
    success2 = send_analysis_email('delivered@resend.dev', 'testuser', test_data)
    print(f"\n Test 2 Result: {' Success' if success2 else ' Failed'}\n")
    
    print("=" * 60)
    print(f"Overall: {' All tests passed!' if success1 and success2 else ' Some tests failed'}")
    print("=" * 60)
