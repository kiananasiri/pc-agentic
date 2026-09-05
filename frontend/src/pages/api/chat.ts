import type { APIRoute } from 'astro';
import { execFile } from 'child_process';
import path from 'path';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { question, analysis, analysis_fundamental, selected_indicators, code = false, model = 'gpt-4o-mini' } = body;

    // Try proxying to Django backend first if available
    try {
      const djangoRes = await fetch('http://127.0.0.1:8000/api/v1/chat/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(3000)
      });
      if (djangoRes.ok) {
        const djangoData = await djangoRes.json();
        return new Response(JSON.stringify(djangoData), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    } catch (_err) {
      // Django server not listening on 8000; execute directly via Agno Python engine
    }

    // Direct invocation via Python Agno Runner
    const pythonScriptPath = path.resolve(process.cwd(), '../chatbot');
    const inputPayload = JSON.stringify({
      user_input: question,
      analysis: analysis || null,
      fundamental: analysis_fundamental || null,
      selected_indicators: selected_indicators || null,
      code: Boolean(code),
      model: model || 'gpt-4o-mini'
    });
    const base64Payload = Buffer.from(inputPayload).toString('base64');

    const pythonCode = `import sys
import os
import json
import base64
sys.path.insert(0, '${pythonScriptPath}')
from dotenv import load_dotenv
load_dotenv('${pythonScriptPath}/.env')
from public_app.src.chat_bot import chat

payload = json.loads(base64.b64decode('${base64Payload}').decode('utf-8'))
result = chat(
    user_input=payload.get('user_input'),
    analysis=payload.get('analysis'),
    fundamental=payload.get('fundamental'),
    selected_indicators=payload.get('selected_indicators'),
    code=payload.get('code'),
    model=payload.get('model')
)
print(json.dumps(result, ensure_ascii=False))
`;

    return new Promise((resolve) => {
      execFile('python3', ['-c', pythonCode], { cwd: pythonScriptPath }, (error, stdout, stderr) => {
        if (error) {
          resolve(new Response(JSON.stringify({ error: stderr || error.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          }));
          return;
        }

        try {
          const stdoutStr = stdout.trim();
          // Extract JSON payload from stdout even if log messages precede it
          const jsonMatch = stdoutStr.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            resolve(new Response(JSON.stringify(parsed), {
              status: 200,
              headers: { 'Content-Type': 'application/json; charset=utf-8' }
            }));
            return;
          }
          throw new Error('No JSON object found in output');
        } catch (parseErr) {
          resolve(new Response(JSON.stringify({ answer: stdout.trim(), price: 0 }), {
            status: 200,
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          }));
        }
      });
    });

  } catch (err: any) {
    return new Response(JSON.stringify({ error: err?.message || 'Server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
