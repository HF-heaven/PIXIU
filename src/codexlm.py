import os
import json
import subprocess
from lm_eval.base import BaseLM
from lm_eval import utils
from tqdm import tqdm

class CodexLM(BaseLM):
    REQ_CHUNK_SIZE = 1  # Codex CLI processes one at a time
    
    def __init__(self, model="gpt-4o", truncate=False):
        """
        :param model: str
            Model name (e.g., "gpt-4o", "gpt-4-turbo")
        :param truncate: bool
            Truncate input if too long (if False and input is too long, throw error)
        """
        super().__init__()
        
        self.model = model
        self.truncate = truncate
        self._tokenizer = None  # Lazy load tokenizer
        self._last_raw_output = None  # Store last raw output for debugging
        self._last_stderr = None  # Store last stderr for debugging
        self._debug_mode = os.environ.get("CODEX_DEBUG", "false").lower() == "true"
        
        # Check for API key
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Verify codex CLI is available
        try:
            result = subprocess.run(
                ["codex", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Codex CLI not working properly")
        except FileNotFoundError:
            raise RuntimeError("Codex CLI not found. Please install with: npm install -g @openai/codex@latest")
        
        # Check login status (optional, but recommended)
        try:
            login_result = subprocess.run(
                ["codex", "login", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if "not logged in" in login_result.stdout.lower() or login_result.returncode != 0:
                print("WARNING: Codex CLI may not be logged in. Run: echo $OPENAI_API_KEY | codex login --with-api-key")
        except Exception:
            pass  # Ignore login check errors
    
    def _get_tokenizer(self):
        """Lazy load tokenizer to avoid import issues."""
        if self._tokenizer is None:
            try:
                import transformers
                self._tokenizer = transformers.GPT2TokenizerFast.from_pretrained("gpt2")
            except Exception as e:
                print(f"Warning: Failed to load tokenizer: {e}. Using fallback.")
                self._tokenizer = "fallback"  # Use fallback mode
        return self._tokenizer
    
    @property
    def tokenizer(self):
        """Get tokenizer (lazy loaded)."""
        return self._get_tokenizer()
    
    @property
    def eot_token_id(self):
        tokenizer = self._get_tokenizer()
        if tokenizer == "fallback":
            return 50256  # GPT-2 EOS token ID
        return tokenizer.eos_token_id
    
    @property
    def max_length(self):
        return 4096
    
    @property
    def max_gen_toks(self):
        return 1024
    
    @property
    def batch_size(self):
        raise NotImplementedError()
    
    @property
    def device(self):
        raise NotImplementedError()
    
    def tok_encode(self, string: str):
        tokenizer = self._get_tokenizer()
        if tokenizer == "fallback":
            # Minimal fallback: return byte encoding
            return list(string.encode('utf-8'))
        return tokenizer.encode(string, add_special_tokens=False)
    
    def tok_decode(self, tokens):
        tokenizer = self._get_tokenizer()
        if tokenizer == "fallback":
            # Minimal fallback: decode from bytes
            try:
                if isinstance(tokens, list):
                    return bytes(tokens).decode('utf-8', errors='ignore')
                return str(tokens)
            except:
                return str(tokens)
        return tokenizer.decode(tokens)
    
    def _loglikelihood_tokens(self, requests, disable_tqdm=False):
        raise NotImplementedError("Codex CLI does not support loglikelihood")
    
    def _call_codex_cli(self, instruction: str) -> str:
        """Call Codex CLI and return the output text."""
        env = os.environ.copy()
        # Ensure OPENAI_API_KEY is set
        if "OPENAI_API_KEY" not in env:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        cmd = [
            "codex", "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--model", self.model,
            "--json",
            "--",
            instruction
        ]
        print("instruction: ", instruction)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300,  # 5 minute timeout
            )
            # Store raw output for debugging (optional, can be accessed via attribute)
            self._last_raw_output = result.stdout
            self._last_stderr = result.stderr
            
            # Debug: print raw output if debug mode is enabled
            if self._debug_mode:
                print(f"\n[DEBUG] Codex CLI Raw Output:")
                print(result.stdout[:1000])
                
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise RuntimeError(f"Codex CLI failed (exit code {result.returncode}): {error_msg}")
            
            # Parse JSON output
            # Codex CLI outputs multiple JSON lines, including events and actual output
            # Format: {"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"actual output"}}
            output_lines = result.stdout.strip().split('\n')
            actual_output = None
            
            # Look for the actual output in item.completed events
            # Process in reverse to get the last (most recent) item.completed
            all_item_outputs = []  # Collect all item.completed outputs
            for line in reversed(output_lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        # Check for item.completed type which contains the actual output
                        if parsed.get("type") == "item.completed":
                            item = parsed.get("item", {})
                            if isinstance(item, dict):
                                # Extract text from item
                                text = item.get("text")
                                if text:
                                    all_item_outputs.append(text)
                                    # Filter out generic greetings/responses
                                    text_lower = text.lower().strip()
                                    generic_responses = [
                                        "how can i assist",
                                        "hi there",
                                        "hello",
                                        "how can i help",
                                        "what can i do",
                                        "how can i assist you with"
                                    ]
                                    if not any(greeting in text_lower for greeting in generic_responses):
                                        actual_output = text
                                        break
                        
                        # Also check for direct "output" field
                        output = parsed.get("output")
                        if output:
                            actual_output = output
                            break
                        
                        # Check for direct "text" field (fallback)
                        if parsed.get("text") and parsed.get("type") != "turn.completed":
                            actual_output = parsed.get("text")
                            break
                except json.JSONDecodeError:
                    # If not JSON, might be plain text output
                    if line and not line.startswith('{'):
                        actual_output = line
                        break
                    continue
            
            # Return found output or use the last item.completed if no non-generic one found
            if actual_output:
                return actual_output
            elif all_item_outputs:
                # If we found item.completed but they were all generic, use the last one anyway
                if self._debug_mode:
                    print(f"[DEBUG] Using last item.completed output (may be generic): {all_item_outputs[-1]}")
                return all_item_outputs[-1]
            
            # If no item.completed found, try to extract from any line with text
            # Sometimes Codex might output in a different format
            for line in output_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        # Look for any text-like field
                        for key in ['text', 'content', 'message', 'output']:
                            if key in parsed and parsed[key]:
                                return str(parsed[key])
                except json.JSONDecodeError:
                    pass
            
            # Last resort: return raw output (might contain multiple JSON lines)
            # But warn if it looks like metadata
            raw_output = result.stdout.strip()
            if "turn.completed" in raw_output and "item.completed" not in raw_output:
                print(f"WARNING: Could not find item.completed in Codex output. Raw output: {raw_output[:200]}...")
            return raw_output
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Codex CLI timed out")
    
    def greedy_until(self, requests):
        """Generate text using Codex CLI."""
        print("================greedy_until=================")
        print("requests: ", requests)
        if not requests:
            return []
        
        print("greedy_until requests: ", requests)
        res = []
        
        def _collate(x):
            toks = self.tok_encode(x[0])
            return len(toks), x[0]
        
        re_ord = utils.Reorderer(requests, _collate)
        print("re_ord: ", re_ord.get_reordered())
        print("================================================")
        
        # Process requests one by one (Codex CLI doesn't support batching)
        for context, until in tqdm(re_ord.get_reordered(), desc="Codex generation"):
            prompt = context
            
            # Clean up prompt - remove "until" suffix if present (from prompt formatting)
            if prompt.endswith("until"):
                prompt = prompt[:-5].rstrip()
            
            try:
                print("prompt: ", prompt)
                output = self._call_codex_cli(prompt)
                print("output: ", output)
                # Debug output if enabled
                if self._debug_mode:
                    print(f"\n[DEBUG] Codex Output for prompt (first 200 chars):")
                    print(f"  Prompt: {prompt[:200]}...")
                    print(f"  Output: {output[:500]}...")
                    if self._last_raw_output:
                        print(f"  Raw output (first 500 chars): {self._last_raw_output[:500]}...")
                
                # Apply until stopping criteria if needed
                if until and until != "</s>":
                    # Find the first occurrence of any until string
                    for stop_str in until:
                        idx = output.find(stop_str)
                        if idx != -1:
                            output = output[:idx]
                            break
                
                # Cache the result
                self.cache_hook.add_partial("greedy_until", (context, until), output)
                res.append(output)
                
            except Exception as e:
                print(f"Error calling Codex CLI: {e}")
                if self._debug_mode and self._last_stderr:
                    print(f"  Stderr: {self._last_stderr[:500]}")
                res.append("")  # Return empty string on error
        
        return re_ord.get_original(res)
    
    def _model_call(self, inps):
        raise NotImplementedError()
    
    def _model_generate(self, context, max_length, eos_token_id):
        raise NotImplementedError()