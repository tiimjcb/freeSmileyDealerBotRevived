# 🔒 Privacy Policy

## Introduction

The **Free Smiley Dealer Bot Revived** (FSD Revived) is committed to respecting the privacy of its users and complying with the General Data Protection Regulation (GDPR). This document outlines what data is collected, why it is collected, and how it is handled.

---

## Data Collected

FSD Revived collects **minimal data** strictly for operational and debugging purposes:

### 1. **Guild ID**  
   - **Purpose:** To identify which Discord server the bot is operating in, for logging and debugging purposes.  
   - **Storage:** Stored in a database to maintain server-specific settings. 

### 2. **User ID**  
   - **Purpose:** To track user interactions with the bot, such as emoji detections and experience points for the leaderboard system.  
   - **Storage:** Stored in a database to maintain experience progression across servers.  
   - **Opt-out:** Users can request to have their data removed by contacting the developers via Discord.  

### 3. **Messages**  
   - **Purpose:** The bot analyzes messages in real time to detect triggers (*such as emojis* or "Friday messages" like *is it Friday?*).  
   - **Storage:** **No part of the message content is stored.**  

### 4. **Messages Sent to Gemini AI**  
   - **When:** Only during an active **chat session** (`/chat_start`).  
   - **Purpose:** Messages sent during a chat session are forwarded to **Gemini AI** to generate responses.  
   - **Storage:** Messages are **not stored** by the bot, but may be used by Google to improve Gemini AI. However, these messages **are not linked to Discord profile data or personal information.**  
   - **Opt-out:** Users who enable the **`/ignore_me`** command are ignored by the bot and their messages are **never sent to Gemini AI**.

---

## Data Usage

The collected data is **not shared**, **sold**, or **used for marketing purposes**. Its sole purpose is to:  

- Debug issues with the bot.  
- Maintain functionality such as experience tracking and leaderboards.  
- Generate responses using Gemini AI **only during active chat sessions**.  

---

## Data Retention

- **User IDs and experience points** are stored **persistently** in a database to maintain user progression.  
- **Guild IDs** are stored for server settings and operational purposes.  
- **Logs** are temporary and automatically deleted after **10 days**.  
- **Messages sent to Gemini AI are not stored by the bot**, but may be used by Google to improve the AI.

---

## User Rights

Since FSD Revived stores **only essential operational data**, users have the following rights:  

- **Opt-out:**  
  - You may request that your **User ID and experience data** be removed from the database by contacting the developers via Discord.  
  - You may prevent the bot from processing your messages entirely by using `/ignore_me`, which ensures your messages are not analyzed or sent to Gemini AI.  
- **Transparency:** If you believe the bot is handling data improperly, please report it via GitHub or to the bot's developers.  

---

## Third Parties

FSD Revived does not share any data with third parties. However:  
- The bot operates on Discord and is subject to [Discord's Privacy Policy](https://discord.com/privacy).  
- Messages sent to Gemini AI during chat sessions may be used by Google to improve the AI but are **not linked to user profiles or personal data**. For more information, refer to [Google's Privacy Policy](https://policies.google.com/privacy).  

---

## Contact

If you have questions about this Privacy Policy or wish to opt out of data collection, please contact the developers via:  

- **GitHub Repository:** [Free Smiley Dealer Bot Revived](https://github.com/tiimjcb/freeSmileyDealerBotRevived)  
- **Discord Contacts:** `@tiim.jcb`  

---

## Changes to This Policy

This Privacy Policy may be updated periodically to reflect changes in bot functionality or legal requirements. Any significant changes will be documented in the [GitHub repository](https://github.com/tiimjcb/freeSmileyDealerBotRevived).  

---

By using this bot, you acknowledge and agree to this Privacy Policy. If you do not agree, please remove the bot from your server.