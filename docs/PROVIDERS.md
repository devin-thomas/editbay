# Providers and local execution

EditBay's hosted MCP supplies documentation. Editing and provider calls run in the caller's environment, not on the hosted service.

| Operation | Local route | Optional external route |
| --- | --- | --- |
| Transcription | A locally installed speech-recognition engine | An explicitly selected transcription API |
| Narration | A stock local voice, or an authorized local voice profile | An explicitly selected speech-generation API |
| Music and effects | User-owned audio or procedural synthesis | Licensed stock or an approved generation service |
| Motion and rendering | HyperFrames and local media tools | A separately configured rendering service |
| Media validation | FFmpeg/ffprobe and EditBay measurements | Human review when automated evidence is insufficient |

Choose engines according to the current tool requirements and verify their operation on your own system. No workstation identity, benchmark, provider balance, private account configuration, voice reference, or model checkpoint is distributed.

API keys belong in your environment or a local secret store. Configuration names the variables, never their values. Provider pricing and account eligibility must be checked at the provider before a paid run. Record the estimate and get approval before making paid calls.

Use a person's voice or likeness only with their authorization. Keep source recordings, consent records, model profiles and generated private audio outside this repository. Do not substitute a different voice silently when a configured engine is unavailable.
