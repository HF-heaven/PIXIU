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
    
    def __init__(self, model="gpt-4o", truncate=False, harbor_mode=False):
        """
        :param model: str
            Model name (e.g., "gpt-4o", "gpt-4-turbo")
        :param truncate: bool
            Truncate input if too long (if False and input is too long, throw error)
        :param harbor_mode: bool
            If True, use Harbor-compatible execution mode (same instruction, file structure, etc.)
        """
        super().__init__()
        
        self.model = model
        self.truncate = truncate
        self.harbor_mode = harbor_mode
        self._tokenizer = None  # Lazy load tokenizer
        self._last_raw_output = None  # Store last raw output for debugging
        self._last_stderr = None  # Store last stderr for debugging
        self._debug_mode = os.environ.get("CODEX_DEBUG", "false").lower() == "true"
        self.current_doc = None  # Store current doc for Harbor mode
        self._harbor_instruction_template = None  # Lazy load instruction template
        self._save_agent_details = False  # Whether to save detailed agent logs
        self._agent_log_base_dir = None  # Base directory for agent logs
        
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
    
    def _load_harbor_instruction(self) -> str:
        """Load Harbor instruction template."""
        if self._harbor_instruction_template is None:
            # Try to load from Harbor adapter template directory
            harbor_template_path = Path("/home/hefan/harbor/adapters/pixiu/template/instruction.md")
            if harbor_template_path.exists():
                self._harbor_instruction_template = harbor_template_path.read_text()
            else:
                # Fallback: use embedded template
                self._harbor_instruction_template = """You are given a financial task instance in `/tests/data/item.json`.

**Important**: You are currently in the `/app` directory, but the input file is located at the absolute path `/tests/data/item.json` (note the leading slash). Do not use relative paths like `tests/data/item.json`.

- Read the JSON file at `/tests/data/item.json` to understand the query and available choices.
- Decide on the single best label according to the task description.
- Write your final answer as plain text to `/app/answer.txt`.

Your answer must exactly match one of the allowed labels."""
        return self._harbor_instruction_template
    
    def _build_item_json(self, doc: dict, dataset_name: str = None, split: str = "test") -> dict:
        """Build Harbor-format item.json from doc object."""
        item_data = {
            "id": doc.get("id", ""),
            "query": doc.get("query") or doc.get("text", ""),
            "dataset": dataset_name or "pixiu",
            "split": split,
        }
        
        # Add label_type if present
        if "label_type" in doc:
            item_data["label_type"] = doc["label_type"]
        
        # Add task-specific fields
        if "choices" in doc:
            item_data["choices"] = list(doc["choices"])
        
        if "tokens" in doc:
            item_data["tokens"] = list(doc["tokens"])
        
        if "labels" in doc:
            item_data["labels"] = list(doc["labels"])
        
        if "relations" in doc:
            item_data["relations"] = list(doc["relations"])
        
        if "expected_score" in doc:
            item_data["expected_score"] = doc["expected_score"]
        
        if "score_range" in doc:
            item_data["score_range"] = list(doc["score_range"])
        
        return item_data
    
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
        
        # Create agent log directory (like Harbor does)
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
            # Build and write item.json
            item_data = self._build_item_json(doc)
            (data_dir / "item.json").write_text(
                json.dumps(item_data, ensure_ascii=False, indent=2)
            )
            
            # Load Harbor instruction template
            instruction = self._load_harbor_instruction()
            
            # Prepare environment
            env = os.environ.copy()
            if "OPENAI_API_KEY" not in env:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            # Execute codex CLI
            # Harbor instruction uses absolute paths: /tests/data/item.json and /app/answer.txt
            # In Harbor's container environment, these are absolute paths from container root.
            # 
            # To replicate this in local environment:
            # - We use temp_dir as the "container root"
            # - We need to modify the instruction to use absolute paths from temp_dir
            #   because Linux absolute paths start from system root, not working directory
            # - OR: We can use the original instruction and let codex resolve paths
            #   (codex might handle this differently)
            #
            # Best approach: Modify instruction to use temp_dir absolute paths
            # This ensures codex can find the files correctly
            instruction_modified = instruction.replace(
                "/tests/data/item.json",
                str(data_dir / "item.json")
            ).replace(
                "/app/answer.txt",
                str(app_dir / "answer.txt")
            )
            
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
                "--model", self.model,
                "--json",
                "--",
                instruction_modified
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
                print(f"[DEBUG] Harbor mode: item.json content:")
                print(json.dumps(item_data, indent=2))
                print(f"[DEBUG] Harbor mode: instruction (with absolute paths):")
                print(instruction_modified)
            
            # Execute with cwd=app_dir (as Harbor does - agent runs in /app directory)
            # The instruction uses absolute paths, so they will resolve correctly
            result = subprocess.run(
                cmd,
                cwd=str(app_dir),  # Set working directory to app_dir (as Harbor does)
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
                print(f"[DEBUG] Harbor mode: codex return code={result.returncode}")
                print(f"[DEBUG] Harbor mode: stdout (first 500 chars):")
                print(result.stdout[:500])
                if result.stderr:
                    print(f"[DEBUG] Harbor mode: stderr (first 500 chars):")
                    print(result.stderr[:500])
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise RuntimeError(f"Codex CLI failed (exit code {result.returncode}): {error_msg}")
            
            # Read answer from answer.txt
            answer_path = app_dir / "answer.txt"
            if answer_path.exists():
                answer = answer_path.read_text().strip()
                if self._debug_mode:
                    print(f"[DEBUG] Harbor mode: read answer from answer.txt: {answer}")
                if answer:  # Only return if answer is not empty
                    return answer
                else:
                    if self._debug_mode:
                        print("[DEBUG] Harbor mode: answer.txt exists but is empty, falling back to stdout parsing")
            
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
        
        if actual_output:
            return actual_output
        elif all_item_outputs:
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
        print("requests: ", requests)
        print(f"[DEBUG] greedy_until received requests type: {type(requests)}")
        print(f"[DEBUG] greedy_until received requests id: {id(requests)}")
        print(f"[DEBUG] greedy_until received requests len: {len(requests) if hasattr(requests, '__len__') else 'N/A'}")
        if not requests:
            print("[DEBUG] greedy_until: requests is empty, returning []")
            return []
        
        print("greedy_until requests: ", requests)
        res = []
        
        def _collate(x):
            toks = self.tok_encode(x[0])
            return len(toks), x[0]
        
        re_ord = utils.Reorderer(requests, _collate)
        print("re_ord: ", re_ord.get_reordered())
        print("================================================")
        
        # Get request docs if available (set by evaluator for Harbor mode)
        request_docs = getattr(self, '_request_docs', None)
        if request_docs is None and self.harbor_mode:
            # Fallback: try to use current_doc for all requests
            request_docs = [self.current_doc] * len(requests) if self.current_doc else None
        
        # For Harbor mode with CachingLM: if request_docs is set but requests is empty (all cached),
        # we still need to process them to save agent details. However, if requests is empty,
        # we can't process anything. The issue is that CachingLM only passes remaining_reqs
        # (uncached requests) to the underlying LM, so if all requests are cached, requests will be empty.
        # In this case, we should still return empty results, but agent details won't be saved.
        # This is expected behavior when using caching.
        
        # Process requests one by one (Codex CLI doesn't support batching)
        for idx, (context, until) in enumerate(tqdm(re_ord.get_reordered(), desc="Codex generation")):
            prompt = context
            
            # Clean up prompt - remove "until" suffix if present (from prompt formatting)
            if prompt.endswith("until"):
                prompt = prompt[:-5].rstrip()
            
            try:
                if self.harbor_mode:
                    # Harbor mode: use doc-based execution
                    # Get the corresponding doc for this request
                    if request_docs and idx < len(request_docs):
                        doc = request_docs[idx]
                    elif self.current_doc:
                        doc = self.current_doc
                    else:
                        raise RuntimeError("Harbor mode requires doc to be set. Make sure evaluator sets lm._request_docs or lm.current_doc before calling greedy_until().")
                    print(f"Harbor mode: using doc-based execution (doc_id={doc.get('id', 'unknown')})")
                    
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