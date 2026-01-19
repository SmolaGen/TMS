import os
import json
import time
import random
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class RetryPolicy:
    initial_interval: float = 1.0
    backoff_factor: float = 2.0
    max_interval: float = 10.0
    max_attempts: int = 3
    jitter: bool = True
    retry_on: tuple = (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError)

class VibeProxyClient:
    def __init__(self, api_key: str, url: str, model: str, retry_policy: Optional[RetryPolicy] = None):
        self.api_key = api_key
        self.url = url
        self.model = model
        self.retry_policy = retry_policy or RetryPolicy()

    def call(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self._chat_with_retry(messages)

    def _chat_with_retry(self, messages: List[Dict[str, str]]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }
        
        data = json.dumps(payload).encode("utf-8")
        
        attempt = 1
        current_interval = self.retry_policy.initial_interval
        
        while attempt <= self.retry_policy.max_attempts:
            try:
                req = urllib.request.Request(f"{self.url}/chat/completions", data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    return res_data['choices'][0]['message']['content']
            
            except self.retry_policy.retry_on as e:
                # Специальная обработка 429 Rate Limit
                is_rate_limit = isinstance(e, urllib.error.HTTPError) and e.code == 429
                
                if attempt == self.retry_policy.max_attempts:
                    print(f"[RALPH] ❌ LLM Call Failed after {attempt} attempts: {e}")
                    raise e
                
                wait_time = current_interval
                if self.retry_policy.jitter:
                    wait_time += random.uniform(0, 0.1 * wait_time)
                
                print(f"[RALPH] ⚠️ LLM Call Failed ({e}). Retrying in {wait_time:.1f}s... (Attempt {attempt}/{self.retry_policy.max_attempts})")
                time.sleep(wait_time)
                
                attempt += 1
                current_interval = min(current_interval * self.retry_policy.backoff_factor, self.retry_policy.max_interval)
                
            except Exception as e:
                print(f"[RALPH] ❌ Unexpected Error in LLM Call: {e}")
                raise e
        
        return ""
