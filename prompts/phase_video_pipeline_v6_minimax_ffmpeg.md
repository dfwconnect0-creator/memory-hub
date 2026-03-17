# Video Pipeline Phrase 6: MiniMax Music & FFmpeg Assembly

## Goal
Implement AI background music generation using MiniMax Audio API and assemble the final MP4 with FFmpeg (original video + ElevenLabs voiceover + MiniMax background music). 

The user already provided their ElevenLabs API key, so we'll start by adding it to \`.env\`.

## 1. Setup API Keys
Before coding anything, add the provided ElevenLabs API key to the project's \`.env\` file.
\`\`\`bash
# Add this line to .env
ELEVENLABS_API_KEY=sk_1cf2e6d08ddfdba3de3cc53d37afd97787eb2eecd3a30337
\`\`\`

## 2. MiniMax Audio Generator (\`src/music_generator.py\`)
1. Create a module to generate background music using MiniMax REST API
2. Expect the \`MINIMAX_API_KEY\` from environment variables
3. When \`--mock-music\` is passed, generate an empty/dummy file instead
4. Implement simple tests pointing to MiniMax logic

## 3. FFmpeg Assembler (\`src/video_assembler.py\`)
1. Create a module that takes the visual MP4 and audio tracks (MP3)
2. Add background audio ducking logic (lower music volume when VO is playing)
3. Output the final assembled video to \`output/videos/final_{video_id}.mp4\`
4. Wrap FFmpeg calls safely in Python using \`subprocess\`

## 4. CLI Integration (\`src/cli.py\`)
1. Update \`src/cli.py\` Video command
2. Add flags: \`--bg-music\` and \`--assemble\`
3. Link the entire pipeline: Convert → Voiceover → Music → FFmpeg

## 5. Tests
1. Ensure unit tests for the assembler logic and the music generator
2. Validate mock flags correctly bypass API calls
