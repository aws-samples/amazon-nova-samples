---
title: Bedrock NotebookLM
emoji: 🎙️
short_description: Personalised Podcasts For All
---

# Bedrock NotebookLM

## Overview

This project is inspired by the NotebookLM tool, and implements it with Bedrock LLMs and Polly text-to-speech models. This tool processes the content of a PDF and/or video files and  generates a natural dialogue suitable for an audio podcast, and outputs it as an MP3 file.

Built with:
- AWS Bedrock
- AWS Polly
- [Jina Reader 🔍](https://jina.ai/reader/)

## Features

- **Convert PDF to Podcast:** Upload a PDF and convert its content into a podcast dialogue.
- **Read PDF directly S3:** Use documents in s3 to convert to podcast
- **Process videos directly:** Directly upload videos to use as content for podcast
- **Engaging Dialogue:** The generated dialogue is designed to be informative and entertaining.
- **User-friendly Interface:** Simple interface using Gradio for easy interaction.

## Installation

To set up the project, follow these steps:

Clone the repo.

1. **Build docker image:**
   ```bash
   ./run.sh build
   ```

3. **Run the app:**
   ```bash
   ./run.sh run
   ```

Access app at `localhost:7860`

![Screenshot](./screenshot.png)