import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config.settings import Settings
import logging
import os
import markdown
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.template_dir = 'templates'
        os.makedirs(self.template_dir, exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def send_email(self, subject, context):
        if not Settings.EMAIL_SENDER or not Settings.EMAIL_PASSWORD:
            logger.warning("Email credentials not set. Skipping email.")
            return

        msg = MIMEMultipart()
        msg['From'] = Settings.EMAIL_SENDER
        msg['To'] = Settings.EMAIL_RECEIVER
        msg['Subject'] = subject

        try:
            template = self.env.get_template('email_template.html')
            
            # Format numbers for display
            formatted_context = context.copy()
            formatted_context['total_value'] = f"{context['total_value']:,.2f}"
            
            # Convert AI markdown to HTML
            if 'ai_analysis' in formatted_context and formatted_context['ai_analysis']:
                 formatted_context['ai_analysis'] = markdown.markdown(formatted_context['ai_analysis'])
            
            # Format suggestions list
            suggestions_list = []
            for _, row in context['suggestions'].iterrows():
                suggestions_list.append({
                    'category': row['category'],
                    'current_pct': f"{row['current_pct']:.1f}",
                    'target_pct': f"{row['target_pct']:.1f}",
                    'status': row['status']
                })
            formatted_context['suggestions'] = suggestions_list
            
            # Format contribution
            if isinstance(context['contribution'], str):
                formatted_context['contribution_is_str'] = True
                formatted_context['contribution'] = context['contribution']
            else:
                formatted_context['contribution_is_str'] = False
                contribution_list = []
                for _, row in context['contribution'].iterrows():
                    contribution_list.append({
                        'category': row['category'],
                        'contribution': f"{row['contribution']:,.2f}"
                    })
                formatted_context['contribution'] = contribution_list

            html_content = template.render(formatted_context)
            msg.attach(MIMEText(html_content, 'html'))
            
        except Exception as e:
            logger.error(f"Error rendering email template: {e}")
            # Fallback to simple text if template fails
            msg.attach(MIMEText("Erro ao gerar relatório HTML. Verifique os logs.", 'plain'))

        try:
            # Gmail SMTP
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(Settings.EMAIL_SENDER, Settings.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            logger.info("Email sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

