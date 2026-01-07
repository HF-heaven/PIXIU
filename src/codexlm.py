import os
import json
import subprocess
import shutil
import uuid
from pathlib import Path
from lm_eval.base import BaseLM
from lm_eval import utils
from tqdm import tqdm

class CodexLM(BaseLM):
    REQ_CHUNK_SIZE = 1  # Codex CLI processes one at a time
    
    def __init__(self, model="gpt-4o", truncate=False, harbor_mode=False, use_docker=True):
        """
        :param model: str
            Model name (e.g., "gpt-4o", "gpt-4-turbo")
        :param truncate: bool
            Truncate input if too long (if False and input is too long, throw error)
        :param harbor_mode: bool
            If True, use Harbor-compatible execution mode (same instruction, file structure, etc.)
        :param use_docker: bool
            If True, run codex CLI inside Docker container (matching Harbor exactly)
        """
        super().__init__()
        
        self.model = model
        self.truncate = truncate
        self.harbor_mode = harbor_mode
        self.use_docker = use_docker
        self._tokenizer = None  # Lazy load tokenizer
        self._last_raw_output = None  # Store last raw output for debugging
        self._last_stderr = None  # Store last stderr for debugging
        self._debug_mode = os.environ.get("CODEX_DEBUG", "false").lower() == "true"
        self.current_doc = None  # Store current doc for Harbor mode
        self._harbor_instruction_template = None  # Lazy load instruction template
        self._save_agent_details = False  # Whether to save detailed agent logs
        self._agent_log_base_dir = None  # Base directory for agent logs
        self._docker_image_built = False  # Track if Docker image is built
        
        # Check for API key
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Verify codex CLI is available (or Docker if use_docker=True)
        if use_docker:
            # Check if Docker is available
            try:
                result = subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    raise RuntimeError("Docker not working properly")
            except FileNotFoundError:
                raise RuntimeError("Docker not found. Please install Docker to use Docker mode.")
        else:
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
    
    def _load_harbor_instruction(self, query: str) -> str:
        """Load Harbor instruction template (adapted for native execution without Docker).
        
        Original Harbor uses absolute paths (/app/answer.txt)
        which work in Docker containers. For native execution, we use relative paths.
        """
        instruction = f"""=== YOUR TASK ===
You are given a financial task.
You MUST follow the following STEP GUIDE to complete the task.
Examine your answer with a program called check_answer.py under the same directory, and iterate until it's passed.
When running a command, **NO LEADING QUOTATION MARK** (e.g., ' or ") should be provided, just provide the command.
Try to add `bash -lc` before the command if you keep encountering the error.

=== STEP GUIDE ===
1. Understand the task.
2. Provide your answer.
3. Use `python write_answer.py "ANSWER"` to save the answer.
4. Run `python check_answer.py` to check the answer.
5. If the tests fail, analyze the errors and repeat steps 3-4 until the tests pass.

=== TASK DESCRIPTION ===
{query}
"""
        return instruction
    
    def _infer_label_type(self, doc: dict) -> str:
        """Infer the task type based on doc structure."""
        if "tokens" in doc and "labels" in doc:
            return "sequence labeling (NER/POS)"
        elif "relations" in doc:
            return "relation extraction"
        elif "expected_score" in doc or "score_range" in doc:
            return "regression/scoring"
        elif "choices" in doc and len(doc.get("choices", [])) > 0:
            # Detect sentiment vs general classification
            choices_str = " ".join(str(c).lower() for c in doc["choices"])
            if any(word in choices_str for word in ["positive", "negative", "neutral"]):
                return "sentiment analysis"
            return "classification"
        elif "summary" in doc.get("query", "").lower() or "summarize" in doc.get("query", "").lower():
            return "summarization"
        else:
            return "question answering"
    
    
    def _call_codex_cli_harbor_mode(self, doc: dict, context: str = None, save_agent_details: bool = False, agent_log_dir: Path = None) -> str:
        """Call Codex CLI in Harbor mode: create temp dir, write item.json, use instruction.md, read answer.txt.
        
        :param save_agent_details: If True, save detailed agent execution logs (like Harbor does)
        :param agent_log_dir: Directory to save agent details (if None, uses temp_dir/agent)
        """
        # Create temporary directory structure
        # Use a unique temp directory that will serve as the root
        temp_dir = Path(f"/tmp/pixiu_codex_{uuid.uuid4().hex}")
        app_dir = temp_dir / "app"
        data_dir = temp_dir / "tests" / "data"
        app_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy helper scripts (check_answer.py and write_answer.py) from Harbor template
        # Harbor provides these in each dataset's environment/ directory
        harbor_template_dir = Path("/home/hefan/PIXIU/src")
        if harbor_template_dir.exists():
            for script in ["check_answer.py", "write_answer.py"]:
                src = harbor_template_dir / script
                if src.exists():
                    shutil.copy(src, temp_dir / script)
                    if self._debug_mode:
                        print(f"[DEBUG] Copied {script} from Harbor template to {temp_dir}")
        if save_agent_details:
            if agent_log_dir is None:
                agent_log_dir = temp_dir / "agent"
            else:
                agent_log_dir = Path(agent_log_dir)
            agent_log_dir.mkdir(parents=True, exist_ok=True)
            print(f"[DEBUG] _call_codex_cli_harbor_mode: Created agent_log_dir: {agent_log_dir}")
        else:
            print(f"[DEBUG] _call_codex_cli_harbor_mode: save_agent_details is False, skipping agent log creation")
        
        try:
            # Build instruction from query
            query = doc.get("query") or doc.get("text", "")
            # print(f"[DEBUG] _call_codex_cli_harbor_mode: query: {query}")
            instruction = self._load_harbor_instruction(query)
            
            # Prepare environment
            env = os.environ.copy()
            if "OPENAI_API_KEY" not in env:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            # Prepare command (like Harbor does)
            # Command 0: Create auth.json (like Harbor command-0)
            if save_agent_details:
                command_0_dir = agent_log_dir / "command-0"
                command_0_dir.mkdir(parents=True, exist_ok=True)
                
                auth_cmd = f'''cat >"$CODEX_HOME/auth.json" <<EOF
{{
  "OPENAI_API_KEY": "${{OPENAI_API_KEY}}"
}}
EOF'''
                (command_0_dir / "command.txt").write_text(auth_cmd)
                
                # Execute auth command
                auth_result = subprocess.run(
                    ["bash", "-c", auth_cmd],
                    cwd=str(app_dir),
                    capture_output=True,
                    text=True,
                    env=env,
                )
                (command_0_dir / "return-code.txt").write_text(str(auth_result.returncode))
                if auth_result.stdout:
                    (command_0_dir / "stdout.txt").write_text(auth_result.stdout)
                if auth_result.stderr:
                    (command_0_dir / "stderr.txt").write_text(auth_result.stderr)
            
            # Command 1: Execute codex (like Harbor command-1)
            cmd = [
                "codex", "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "--cd", str(temp_dir),  # Set temp_dir as working root - agent sees it as filesystem root
                "--model", self.model,
                "--json",
                "--",
                instruction
            ]
            
            if save_agent_details:
                command_1_dir = agent_log_dir / "command-1"
                command_1_dir.mkdir(parents=True, exist_ok=True)
                (command_1_dir / "command.txt").write_text(" ".join(cmd))
            
            if self._debug_mode:
                print(f"[DEBUG] Harbor mode: temp_dir={temp_dir}")
                print(f"[DEBUG] Harbor mode: app_dir={app_dir}")
                print(f"[DEBUG] Harbor mode: data_dir={data_dir}")
                print(f"[DEBUG] Harbor mode: item.json path={data_dir / 'item.json'}")
                print(f"[DEBUG] Harbor mode: answer.txt path={app_dir / 'answer.txt'}")
                if save_agent_details:
                    print(f"[DEBUG] Harbor mode: agent_log_dir={agent_log_dir}")
                print(f"[DEBUG] Harbor mode: instruction (with query embedded):")
            print(instruction)
            
            # Execute codex CLI (native or Docker)
            if self.use_docker:
                # Run codex in Docker container
                print(f"[Docker] Running codex CLI in Docker container")
                result = self._run_codex_in_docker(
                    temp_dir=temp_dir,
                    app_dir=app_dir,
                    data_dir=data_dir,
                    instruction=instruction,
                    env=env,
                    save_agent_details=save_agent_details,
                    command_1_dir=command_1_dir if save_agent_details else None
                )
            else:
                # Run codex natively
                # With --cd flag, codex treats temp_dir as the working root
                # No need to set cwd here since codex handles it internally
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=300,  # 5 minute timeout
                )
            
            # Save command-1 details (like Harbor does)
            if save_agent_details:
                (command_1_dir / "return-code.txt").write_text(str(result.returncode))
                if result.stdout:
                    (command_1_dir / "stdout.txt").write_text(result.stdout)
                if result.stderr:
                    (command_1_dir / "stderr.txt").write_text(result.stderr)
                
                # Save codex.txt (like Harbor does) - contains the full JSON output
                (agent_log_dir / "codex.txt").write_text(result.stdout)
            
            # Store raw output for debugging
            self._last_raw_output = result.stdout
            self._last_stderr = result.stderr
            
            if self._debug_mode:
                mode = "Docker" if self.use_docker else "Native"
                print(f"[DEBUG] Harbor mode ({mode}): codex return code={result.returncode}")
                print(f"[DEBUG] Harbor mode ({mode}): stdout (first 500 chars):")
                print(result.stdout[:500])
                if result.stderr:
                    print(f"[DEBUG] Harbor mode ({mode}): stderr (first 500 chars):")
                    print(result.stderr[:500])
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise RuntimeError(f"Codex CLI failed (exit code {result.returncode}): {error_msg}")
            
            # Read answer from answer.txt
            answer_path = app_dir / "answer.txt"
            answer_from_file = None
            if answer_path.exists():
                try:
                    answer_from_file = answer_path.read_text().strip()
                    if self._debug_mode:
                        print(f"[DEBUG] Harbor mode: read answer from answer.txt: {answer_from_file}")
                    if answer_from_file:  # Only return if answer is not empty
                        return answer_from_file
                    else:
                        print(f"[WARNING] Harbor mode: answer.txt exists but is empty for doc_id={doc.get('id', 'unknown')}")
                        if self._debug_mode:
                            print("[DEBUG] Harbor mode: answer.txt exists but is empty, falling back to stdout parsing")
                except Exception as e:
                    print(f"[WARNING] Harbor mode: Failed to read answer.txt for doc_id={doc.get('id', 'unknown')}: {e}")
            else:
                print(f"[WARNING] Harbor mode: answer.txt not found at {answer_path} for doc_id={doc.get('id', 'unknown')}")
            
            # Fallback: try to parse from stdout (for compatibility)
            if self._debug_mode:
                print("[DEBUG] Harbor mode: answer.txt not found or empty, falling back to stdout parsing")
                print(f"[DEBUG] Harbor mode: stdout length={len(result.stdout)}, stderr length={len(result.stderr) if result.stderr else 0}")
            
            # Use the existing parsing logic
            parsed_output = self._parse_codex_output_from_stdout(result.stdout)
            
            if not parsed_output or parsed_output.strip() == "":
                # If still empty, log warning and return empty string
                print(f"[WARNING] Harbor mode: No output found in answer.txt or stdout for doc_id={doc.get('id', 'unknown')}")
                if self._debug_mode:
                    print(f"[DEBUG] Harbor mode: Raw stdout: {result.stdout[:500]}")
                    print(f"[DEBUG] Harbor mode: Raw stderr: {result.stderr[:500] if result.stderr else 'None'}")
                    print(f"[DEBUG] Harbor mode: answer.txt exists: {answer_path.exists()}")
                    if answer_path.exists():
                        print(f"[DEBUG] Harbor mode: answer.txt content: {answer_path.read_text()[:200]}")
            
            return parsed_output if parsed_output else ""
                
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                if self._debug_mode:
                    print(f"[DEBUG] Harbor mode: failed to clean up temp dir: {e}")
    
    def _parse_codex_output_from_stdout(self, stdout: str) -> str:
        """Parse codex output from stdout (fallback when answer.txt is not found)."""
        output_lines = stdout.strip().split('\n')
        actual_output = None
        all_item_outputs = []
        
        for line in reversed(output_lines):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    if parsed.get("type") == "item.completed":
                        item = parsed.get("item", {})
                        if isinstance(item, dict):
                            text = item.get("text")
                            if text:
                                all_item_outputs.append(text)
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
                    
                    output = parsed.get("output")
                    if output:
                        actual_output = output
                        break
                    
                    if parsed.get("text") and parsed.get("type") != "turn.completed":
                        actual_output = parsed.get("text")
                        break
            except json.JSONDecodeError:
                if line and not line.startswith('{'):
                    actual_output = line
                    break
                continue
        
        # Try to extract simple yes/no answer from agent message
        if actual_output:
            # Look for patterns like "The answer is **yes**" or "written to...as \"no\""
            import re
            # Pattern 1: "answer is **yes**" or "answer is yes" or "label is **no**"
            match = re.search(r'\b(?:answer|label|result|prediction)\s+(?:is|determined|saved as)\s+(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', actual_output, re.IGNORECASE)
            if match:
                return match.group(1).lower()
            
            # Pattern 2: "written to...as **yes**" or "written as \"no\""
            match = re.search(r'\b(?:written|saved|stored)\s+(?:to|as)\s+.*?(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', actual_output, re.IGNORECASE)
            if match:
                return match.group(1).lower()
            
            # Pattern 3: quoted yes/no anywhere in message
            match = re.search(r'["`\*]+(yes|no)["`\*]+', actual_output, re.IGNORECASE)
            if match:
                return match.group(1).lower()
            
            # Pattern 4: Extract sentiment labels (positive/negative/neutral) - for FPB and similar tasks
            # Look for the label at the end of the message (after final newline or standalone)
            sentiment_match = re.search(r'\b(positive|negative|neutral)\s*$', actual_output, re.IGNORECASE | re.MULTILINE)
            if sentiment_match:
                return sentiment_match.group(1).lower()
            
            # Pattern 5: Look for sentiment labels in quotes or emphasized
            sentiment_match = re.search(r'(?:\*\*|["`])(positive|negative|neutral)(?:\*\*|["`])', actual_output, re.IGNORECASE)
            if sentiment_match:
                return sentiment_match.group(1).lower()
            
            # If no pattern matched, return the full text
            return actual_output
        elif all_item_outputs:
            # Try the same extraction on all collected outputs
            for output in reversed(all_item_outputs):
                import re
                match = re.search(r'\b(?:answer|label|result|prediction|written|saved)\s+(?:is|determined|as|to)\s+(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', output, re.IGNORECASE)
                if match:
                    return match.group(1).lower()
            return all_item_outputs[-1]
        
        # Last resort: return raw output
        return stdout.strip()
    
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
        # print("requests: ", requests)
        print(f"[DEBUG] greedy_until received requests type: {type(requests)}")
        print(f"[DEBUG] greedy_until received requests id: {id(requests)}")
        print(f"[DEBUG] greedy_until received requests len: {len(requests) if hasattr(requests, '__len__') else 'N/A'}")
        if not requests:
            print("[DEBUG] greedy_until: requests is empty, returning []")
            return []
        
        # print("greedy_until requests: ", requests)
        res = []
        
        # Get request docs if available (set by evaluator for Harbor mode)
        request_docs = getattr(self, '_request_docs', None)
        if request_docs is None and self.harbor_mode:
            # Fallback: try to use current_doc for all requests
            request_docs = [self.current_doc] * len(requests) if self.current_doc else None
        
        # Note: CodexLM doesn't support batching (REQ_CHUNK_SIZE = 1), so we don't need to reorder
        # requests for optimization. Reordering would break the mapping between requests and docs
        # in Harbor mode. We process requests in their original order.
        
        # For Harbor mode with CachingLM: if request_docs is set but requests is empty (all cached),
        # we still need to process them to save agent details. However, if requests is empty,
        # we can't process anything. The issue is that CachingLM only passes remaining_reqs
        # (uncached requests) to the underlying LM, so if all requests are cached, requests will be empty.
        # In this case, we should still return empty results, but agent details won't be saved.
        # This is expected behavior when using caching.
        
        # Process requests one by one (Codex CLI doesn't support batching)
        # Process in original order to maintain correct doc mapping
        for idx, (context, until) in enumerate(tqdm(requests, desc="Codex generation")):
            prompt = context
            
            # Clean up prompt - remove "until" suffix if present (from prompt formatting)
            if prompt.endswith("until"):
                prompt = prompt[:-5].rstrip()
            
            try:
                if self.harbor_mode:
                    # Harbor mode: use doc-based execution
                    # Get the corresponding doc for this request (idx matches original order since we don't reorder)
                    if request_docs and idx < len(request_docs):
                        doc = request_docs[idx]
                    elif self.current_doc:
                        doc = self.current_doc
                    else:
                        raise RuntimeError("Harbor mode requires doc to be set. Make sure evaluator sets lm._request_docs or lm.current_doc before calling greedy_until().")
                    print(f"Harbor mode: using doc-based execution (doc_id={doc.get('id', 'unknown')}, idx={idx})")
                    
                    # Determine agent log directory if saving details
                    agent_log_dir = None
                    if self._save_agent_details and self._agent_log_base_dir:
                        doc_id = doc.get('id', f'doc_{idx}')
                        agent_log_dir = Path(self._agent_log_base_dir) / f"agent_{doc_id}"
                        print(f"[DEBUG] CodexLM: Saving agent details for doc_id={doc_id}")
                        print(f"[DEBUG]   agent_log_dir: {agent_log_dir}")
                    else:
                        print(f"[DEBUG] CodexLM: Agent details saving disabled")
                        print(f"[DEBUG]   _save_agent_details: {self._save_agent_details}")
                        print(f"[DEBUG]   _agent_log_base_dir: {self._agent_log_base_dir}")
                    
                    output = self._call_codex_cli_harbor_mode(
                        doc, 
                        context,
                        save_agent_details=self._save_agent_details,
                        agent_log_dir=agent_log_dir
                    )
                    print("Harbor mode output: ", output)
                else:
                    # Original mode: use prompt-based execution
                    # print("prompt: ", prompt)
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
        
        # No need to reorder results since we processed requests in original order
        return res
    
    def _build_docker_image(self):
        """Build Docker image for running codex CLI (matching Harbor setup)."""
        if self._docker_image_built:
            return
            
        print("[Docker] Building Docker image...")
        
        # Use Harbor's PIXIU adapter Dockerfile
        dockerfile_dir = Path("/home/hefan/harbor/adapters/pixiu/template/environment")
        if not dockerfile_dir.exists():
            raise RuntimeError(f"Harbor PIXIU Dockerfile not found at {dockerfile_dir}")
        
        dockerfile_path = dockerfile_dir / "Dockerfile"
        if not dockerfile_path.exists():
            raise RuntimeError(f"Dockerfile not found at {dockerfile_path}")
        
        # Build image
        build_cmd = [
            "docker", "build",
            "-t", "pixiu-codex-env",
            "-f", str(dockerfile_path),
            str(dockerfile_dir)
        ]
        
        if self._debug_mode:
            print(f"[DEBUG] Docker build command: {' '.join(build_cmd)}")
        
        result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for build
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker build failed: {result.stderr}")
        
        self._docker_image_built = True
        print("[Docker] Image built successfully")
    
    def _run_codex_in_docker(
        self,
        temp_dir: Path,
        app_dir: Path,
        data_dir: Path,
        instruction: str,
        env: dict,
        save_agent_details: bool = False,
        command_1_dir: Path = None
    ) -> subprocess.CompletedProcess:
        """Run codex CLI with Docker container (matching Harbor execution).
        
        Harbor's approach:
        1. Start a long-running Docker container with helper scripts
        2. Run codex CLI on the host
        3. Codex CLI uses `docker exec` to run commands inside the container
        
        We simplify by:
        1. Creating a temporary container for the duration of one task
        2. Running codex CLI on host with proper shell configuration
        3. Using container name as the execution target
        """
        
        # Ensure Docker image is built
        self._build_docker_image()
        
        # Create a unique container name
        container_name = f"pixiu-codex-{uuid.uuid4().hex[:8]}"
        
        try:
            # Start a long-running container
            start_cmd = [
                "docker", "run",
                "-d",  # Detached mode
                "--name", container_name,
                "-v", f"{temp_dir.absolute()}:/workspace",
                "-v", f"{app_dir.absolute()}:/app",
                "-v", f"{data_dir.absolute()}:/data",
                "-w", "/app",  # Set /app as default working directory
                "-e", f"OPENAI_API_KEY={env['OPENAI_API_KEY']}",
                "pixiu-codex-env",
                "sleep", "infinity"  # Keep container running
            ]
            
            if self._debug_mode:
                print(f"[DEBUG] Starting Docker container: {container_name}")
                print(f"[DEBUG] Command: {' '.join(start_cmd)}")
            
            start_result = subprocess.run(
                start_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if start_result.returncode != 0:
                raise RuntimeError(f"Failed to start Docker container: {start_result.stderr}")
            
            if self._debug_mode:
                print(f"[DEBUG] Container {container_name} started successfully")
            
            # Run codex CLI on host, but configure it to execute commands inside Docker
            # Codex CLI runs on host, but we set SHELL environment variable to use docker exec
            # This way codex CLI will execute all commands inside the container
            
            # Create a shell wrapper script that executes commands in Docker
            exec_wrapper = temp_dir / "docker_exec_wrapper.sh"
            exec_wrapper.write_text(f"""#!/bin/bash
# Wrapper script to execute commands inside Docker container
# This is used by codex CLI to run commands in the container
exec docker exec -w /workspace -i {container_name} bash -lc "$@"
""")
            exec_wrapper.chmod(0o755)
            
            # Set SHELL environment variable so codex CLI uses our wrapper
            docker_env = env.copy()
            docker_env["SHELL"] = str(exec_wrapper.absolute())
            
            # Run codex CLI on host - it will use docker exec via SHELL wrapper
            codex_cmd = [
                "codex", "exec",
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
                "--cd", str(temp_dir),  # Codex sees temp_dir as root
                "--model", self.model,
                "--json",
                "--",
                instruction
            ]
            
            if save_agent_details and command_1_dir:
                (command_1_dir / "command.txt").write_text(" ".join(codex_cmd))
            
            if self._debug_mode:
                print(f"[DEBUG] Running codex with Docker execution:")
                print(f"  Command: {' '.join(codex_cmd)}")
                print(f"  Container: {container_name}")
                print(f"  Shell wrapper: {exec_wrapper}")
                print(f"  Workspace: /workspace (mapped from {temp_dir})")
                print(f"  App dir: /app (mapped from {app_dir})")
                print(f"  Data dir: /data (mapped from {data_dir})")
            
            # Run codex CLI on host - commands will execute inside Docker via SHELL wrapper
            result = subprocess.run(
                codex_cmd,
                capture_output=True,
                text=True,
                env=docker_env,  # Use modified env with SHELL wrapper
                cwd=str(temp_dir),
                timeout=300  # 5 minute timeout
            )
            
            return result
            
        finally:
            # Clean up: stop and remove container
            cleanup_cmd = ["docker", "rm", "-f", container_name]
            subprocess.run(
                cleanup_cmd,
                capture_output=True,
                timeout=30
            )
            if self._debug_mode:
                print(f"[DEBUG] Cleaned up container {container_name}")
    
    def _model_call(self, inps):
        raise NotImplementedError()
    
    def _model_generate(self, context, max_length, eos_token_id):
        raise NotImplementedError()