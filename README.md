# Voice Master

A free Discord bot that gives you premium temporary voice channel features with an interactive button panel. 

I built this repository for anyone wanting an automated voice system for their server, or for developers trying to figure out how to code this themselves. A lot of people struggle with keeping button interactions working and saving channel data when the bot restarts. This project fixes those exact issues.

## How it works
The bot handles the entire cycle: it detects when someone joins the setup channel, creates a new room, moves them into it, and cleans up by deleting the channel the second the last person leaves. 

Channel owners can manage everything directly from the message interface:
* Lock / Unlock rooms
* Hide / Unhide channels
* Rename rooms
* Change user limits
* Alot more

## Setup & Configuration

1. **Add your token:** Open up the code and drop your Discord bot token into the placeholder on **line 10**.
2. **Customize (Optional):** You can change the default emojis to match your server's theme.

## Commands

* The default prefix is `,` (you can change this to whatever you want in the code).
* To get started, just run:
  
```text
  ,voicemaster
```
<img width="518" height="429" alt="592029384-e6e679fa-e3c7-488c-a424-f08abb53d84d (1)" src="https://github.com/user-attachments/assets/518d86d3-39ef-44db-9c87-e23a43090315" />

NOTE: USE DISCORD.PY 3.9.6 FOR THE BEST EXPERIENCE

## 📜 License
This project is licensed for **Personal Use Only**. Commercial use, redistribution for profit, or selling this interface as a "service" is strictly prohibited. See the `LICENSE` file for full details.
