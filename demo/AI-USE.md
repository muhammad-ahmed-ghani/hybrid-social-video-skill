Director: claude-sonnet-5-5 (Claude Sonnet 5.5) (wrote the plan, script and code).

| Role | Model | Tool | Provider | Runs | Used for | Beats |
|---|---|---|---|---|---|---|
| image | nano-banana-pro | ImagineArt MCP generate_image | ImagineArt | hosted | host portrait | 1,2,3,4,5,6,7,8 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 1 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 2 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 3 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 4 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 5 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 6,7 |
| host | veo-3.1-fast | ImagineArt MCP generate_video | ImagineArt (Google Veo) | hosted | talking host clip, native speech | 8 |
| tts (not in the output) | ElevenLabs v3 (Roger) | ImagineArt MCP generate_speech | ImagineArt | hosted | voice test only, not in the final video | - |
| stt | Systran/faster-whisper-base.en | faster-whisper | local | local | word timings and clip trimming from the host audio | 1,2,3,4,5,6,7,8 |
| music (not AI) | - | ffmpeg and numpy | local | local | synthesised pad, ticks, hit and whooshes (no samples) | - |
| code | claude-sonnet-5-5 | claude-sonnet-5-5 | Anthropic | hosted | beat map, script, overlay page, build scripts | - |
| image (not in the output) | gpt-image-2.5-flare | ImagineArt MCP generate_image | ImagineArt | hosted | README mascot (not in the video) | - |

Disclosure: LABEL: photoreal AI-generated people or scenes appear (a fictional presenter). Turn on the platform's AI-content label and say so in the description.
Disclosure: NOTE: the host's face and speech are AI-generated; say so in the description (the platform label covers the face, the line covers the voice).
Data sent to hosted providers: one sentence of the script; portrait image, spoken line; text prompt; the request and project files.
