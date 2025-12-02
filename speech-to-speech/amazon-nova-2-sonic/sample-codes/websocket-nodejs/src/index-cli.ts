import { fromIni } from "@aws-sdk/credential-providers";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { NovaSonicBidirectionalStreamClient } from "./client";
import { randomUUID } from "crypto";

const AWS_PROFILE_NAME = 'bedrock-test';
const AUDIO_FILE_PATH = './input-audio-example/japan16k.raw';
const OUTPUT_DIR = './output';
const CHUNK_SIZE = 1024; // Size of audio chunks in bytes

async function main() {
    try {
        // Create output directory if needed
        if (!existsSync(OUTPUT_DIR)) {
            mkdirSync(OUTPUT_DIR);
            console.log(`Created output directory: ${OUTPUT_DIR}`);
        }

        console.log("Reading audio file...");
        const audioData = readFileSync(AUDIO_FILE_PATH);
        console.log(`Audio file read: ${audioData.length} bytes`);

        console.log(`Creating audio byte chunks of ${CHUNK_SIZE} bytes`);
        const chunks = [];
        for (let offset = 0; offset < audioData.length; offset += CHUNK_SIZE) {
            const chunkLength = Math.min(CHUNK_SIZE, audioData.length - offset);
            const chunk = Buffer.from(audioData.slice(offset, offset + chunkLength));
            chunks.push(chunk);
        }
        console.log(`Audio byte chunks created: ${chunks.length}`);

        console.log("Creating Nova Sonic client...");
        const s2sClient = new NovaSonicBidirectionalStreamClient({
            requestHandlerConfig: {
                maxConcurrentStreams: 10,
            },
            clientConfig: {
                region: "us-east-1",
                credentials: fromIni({ profile: AWS_PROFILE_NAME })
            }
        });

        // Create a session for this streaming operation with unique ID
        const sessionId = `cli-session-${Date.now()}`;
        const session = s2sClient.createStreamSession(sessionId);
        s2sClient.initiateBidirectionalStreaming(sessionId);

        // Track output data
        let transcription = '';
        let analyzedAudio = '';
        let audioResponse = '';
        let toolUseId = null;

        // Set up event handlers for session

        session.onEvent('textOutput', (data) => {
            console.log("\nText output:", data.content);
            const role = data.role;
            if (role === "USER" || role === "ASSISTANT") {
                transcription += `${role}: ${data.content}\n`;
            }
        });

        session.onEvent('audioOutput', (data) => {
            console.log("Audio output received, length:", data.contentId);
            audioResponse += data.content;
        });

        session.onEvent('toolUse', (data) => {
            console.log("Tool being used:", data.toolName);
            console.log("Tool parameters:", JSON.stringify(data));
            toolUseId = data.toolUseId;
        });

        session.onEvent('toolResult', (data) => {
            console.log("\nTool result received:", data);
            analyzedAudio = typeof data.content === 'string' ?
                data.content : JSON.stringify(data.content);
        });

        session.onEvent('contentStart', (data) => {
            if (data.type === 'AUDIO') {
                console.log("Audio output started");
            }
        });


        session.onEvent('contentEnd', async (data) => {
            if (data.type === 'AUDIO' && data.stopReason === 'END_TURN') {
                console.log("Audio output ended, saving to file...");
                const buffer = Buffer.from(audioResponse, 'base64');
                writeFileSync(join(OUTPUT_DIR, "output-audio.raw"), buffer);
                console.log(`Audio saved to: ${join(OUTPUT_DIR, 'output-audio.raw')}`);
                console.log("To convert to WAV: ffmpeg -f s16le -ar 24000 -ac 1 -i output-audio.raw output-audio.wav");
                audioResponse = '';

                await endSession();
            }

        });

        // Helper function to end the session cleanly
        async function endSession() {
            // Wait a moment for any final events
            await new Promise(resolve => setTimeout(resolve, 1000));

            await session.endPrompt();
            console.log('Prompt ended');

            // Wait for any final events after prompt end
            await new Promise(resolve => setTimeout(resolve, 1000));

            await session.close();
            console.log('Session closed');
        }

        session.onEvent('error', (error) => {
            console.error("\nError occurred:", error);
        });

        session.onEvent('streamComplete', () => {
            console.log("\nStream processing completed");

            // Save transcription to file
            if (transcription) {
                writeFileSync(join(OUTPUT_DIR, 'transcription.txt'), transcription);
                console.log(`Transcription saved to: ${join(OUTPUT_DIR, 'transcription.txt')}`);
            }

            // Save analysis result to file if available
            if (analyzedAudio) {
                writeFileSync(join(OUTPUT_DIR, 'analysis.txt'), analyzedAudio);
                console.log(`Analysis saved to: ${join(OUTPUT_DIR, 'analysis.txt')}`);
            }
        });

        console.log('Starting event sequence: Prompt Start -> System Prompt -> Audio Start');

        // Setting up the initial events in sequence
        await session.setupSessionAndPromptStart();
        console.log("Prompt start event sent");

        await session.setupSystemPrompt();
        console.log("System prompt event sent");

        await session.setupStartAudio();
        console.log("Audio start event sent");

        console.log("Starting to stream audio chunks...");
        // Stream audio chunks with a small delay
        for (let i = 0; i < chunks.length; i++) {
            const chunk = chunks[i];
            await session.streamAudio(chunk);

            // Show progress every 10%
            if (i % Math.ceil(chunks.length / 10) === 0 || i === chunks.length - 1) {
                const percent = Math.round((i + 1) / chunks.length * 100);
                console.log(`Progress: ${percent}% (${i + 1}/${chunks.length} chunks)`);
            }

            await new Promise(resolve => setTimeout(resolve, 30)); // 30ms delay between chunks
        }

        // Wait before ending input content to ensure all chunks are processed
        console.log("All audio chunks sent, waiting before ending input content...");
        await new Promise(resolve => setTimeout(resolve, 5000));

        // End audio input content properly - this signals the end of the audio input stream
        await session.endAudioContent();
        console.log("Audio input content ended");

        // Wait for processing to complete - DO NOT end the prompt/session here
        console.log("Waiting for server to process all audio and generate responses...");


    } catch (error) {
        console.error("Error in main function:", error);
        process.exit(1);
    }
}

// Add proper error handling for unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
});

main().catch(err => {
    console.error("Unhandled error in main:", err);
    process.exit(1);
});