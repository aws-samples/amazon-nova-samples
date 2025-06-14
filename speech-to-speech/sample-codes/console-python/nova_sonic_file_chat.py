import os
import json
import asyncio

from nova_sonic_tool_use import (
    BedrockStreamManager,
    AudioStreamer,
    time_it_async,
    DEBUG,
)

class FileChatStreamManager(BedrockStreamManager):
    """Stream manager with a tool for reading local text files."""
    
    def __init__(self, model_id, region, target_file_path=None):
        super().__init__(model_id, region)
        self.target_file_path = target_file_path

    def start_prompt(self):
        read_file_schema = json.dumps({
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to a local text file"}
            },
            "required": ["path"],
        })

        prompt_start_event = {
            "event": {
                "promptStart": {
                    "promptName": self.prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": 24000,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH",
                    },
                    "toolUseOutputConfiguration": {"mediaType": "application/json"},
                    "toolConfiguration": {
                        "tools": [
                            {
                                "toolSpec": {
                                    "name": "readFileTool",
                                    "description": f"Return the contents of the target file: {self.target_file_path or 'No file specified'}",
                                    "inputSchema": {"json": read_file_schema},
                                }
                            }
                        ]
                    },
                }
            }
        }

        return json.dumps(prompt_start_event)

    async def processToolUse(self, toolName, toolUseContent):
        if toolName.lower() == "readfiletool":
            # Use the target file path if specified, otherwise try to get from content
            if self.target_file_path:
                path = self.target_file_path
            else:
                content = toolUseContent.get("content", "{}")
                try:
                    path = json.loads(content).get("path", "")
                except json.JSONDecodeError:
                    path = ""
            
            if not path or not os.path.isfile(path):
                return {"error": f"File '{path}' not found"}
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()
                    return {"fileContent": data[:2000]}
            except Exception as e:
                return {"error": f"Failed to read file: {str(e)}"}
        return await super().processToolUse(toolName, toolUseContent)

async def main(debug=False, file_path=None):
    global DEBUG
    DEBUG = debug

    manager = FileChatStreamManager(model_id="amazon.nova-sonic-v1:0", region="us-east-1", target_file_path=file_path)
    streamer = AudioStreamer(manager)
    
    if file_path:
        print(f"Target file for reading: {file_path}")

    await time_it_async("initialize_stream", manager.initialize_stream)

    try:
        await streamer.start_streaming()
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        await streamer.stop_streaming()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nova Sonic local file chat")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--file", type=str, help="Path to the target file to read")
    args = parser.parse_args()
    try:
        asyncio.run(main(debug=args.debug, file_path=args.file))
    except Exception as e:
        print(f"Application error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
