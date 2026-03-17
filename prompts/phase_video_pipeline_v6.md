# Phase 6: Video Pipeline - MiniMax & FFmpeg Assembly

## Goal
Implement AI background music generation using MiniMax Audio API and assemble the final MP4 with FFmpeg (original video + ElevenLabs voiceover + MiniMax background music).

## Required API Key Setup
Append the ElevenLabs API key to the marketing-agent \`.env\`:
\`\`\`bash
echo 'ELEVENLABS_API_KEY=sk_1cf2e6d08ddfdba3de3cc53d37afd97787eb2eecd3a30337' >> ~/Documents/antigravity/marketing-agent/.env
\`\`\`

## 1. MiniMax Audio Generator (\`src/music_generator.py\`)
1. Create a module to generate background music using MiniMax REST API
2. Expect the \`MINIMAX_API_KEY\` from environment variables
3. When \`--mock-music\` is passed, generate an empty/dummy file instead
4. Implement simple tests pointing to MiniMax logic

## 2. FFmpeg Assembler (\`src/video_assembler.py\`)
1. Create a module that takes the visual MP4 and audio tracks (MP3)
2. Add background audio ducking logic (lower music volume when VO is playing)
3. Output the final assembled video to \`output/videos/final_{video_id}.mp4\`
4. Wrap FFmpeg calls safely in Python passing parameters

## 3. CLI Integration
1. Update \`src/cli.py\` Video command
2. Add flags: \`--bg-music\` and \`--assemble\`
3. Link the entire pipeline: Convert → Voiceover → Music → FFmpeg

## 4. Tests
1. Ensure unit tests for the assembler logic and the music generator
2. Validate mock flags correctly bypass API calls
