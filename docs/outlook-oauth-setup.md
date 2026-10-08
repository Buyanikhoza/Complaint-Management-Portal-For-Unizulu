# Outlook SMTP OAuth setup

Outlook.com SMTP requires Modern Authentication. The application uses an OAuth
refresh token for Outlook senders and keeps password authentication available
for SMTP providers that support it.

## Register the Microsoft app

1. In Microsoft Entra, create an app registration that supports personal
   Microsoft accounts.
2. Enable public client/device-code authentication for the app.
3. Add the delegated `SMTP.Send` permission for Office 365 Exchange Online.
   The setup tool also requests `offline_access`.
4. Put the app's Application (client) ID in the local `.env` file:

   ```env
   EMAIL_AUTH_METHOD=oauth2
   EMAIL_OAUTH_CLIENT_ID=your-application-client-id
   EMAIL_OAUTH_TENANT=consumers
   EMAIL_HOST=smtp-mail.outlook.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=true
   EMAIL_USE_SSL=false
   EMAIL_USERNAME=your-outlook-address
   EMAIL_FROM=your-outlook-address
   ```

5. Run the local setup tool:

   ```powershell
   .\.venv\Scripts\python.exe scripts\setup_outlook_oauth.py
   ```

6. Follow the Microsoft device sign-in instructions shown in the terminal.
   The tool saves the resulting refresh token in `.env` without displaying it.
   Never commit `.env` or share the refresh token.
7. Restart the application and verify `/email_status` reports
   `"configured": true`. Send a one-time test email before deployment.

The production deployment needs its own client ID and refresh token stored in
the host's secret/environment-variable manager; do not copy `.env` into source
control.

## User notification addresses

New accounts must provide an email address at registration. Administrators can
add an email address to existing accounts from the user-management table. The
app stores addresses with user records in its configured user-state store and
uses those saved addresses for grievance confirmations and status updates.
