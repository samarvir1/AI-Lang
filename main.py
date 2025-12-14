# © 2025 Samarvir Singh Vasale

import os
import time
import requests
import json
import subprocess
from pathlib import Path
import re
import graphviz
import shutil
import sys

APP_VERSION = "0.0.5"

PROJECT_TEMPLATES = {
    "1": {
        "name": "Simple CLI Calculator",
        "description": "Create a command-line application that takes two numbers and an operator (+, -, *, /) as input arguments and prints the result. Include basic error handling for invalid input or division by zero."
    },
    "2": {
        "name": "Basic File Reader/Writer",
        "description": "Create a command-line tool that takes two arguments: a filename and a mode ('read' or 'write'). If 'read', print the content of the file. If 'write', prompt the user for text input and write it to the file, overwriting existing content. Handle file not found errors."
    },
    "3": {
        "name": "Simple Web Server (Placeholder)",
        "description": "Create a very basic HTTP web server that listens on port 8080. For any request to the root path ('/'), it should respond with 'Hello, World!' and a 200 OK status. For any other path, it should respond with 'Not Found' and a 404 status."
    }
}

COLOR_ERROR = "red"
COLOR_SUCCESS = "green"
COLOR_WARNING = "yellow"
COLOR_INFO = "cyan"
COLOR_PROMPT = "blue"
COLOR_HEADER = "magenta"
COLOR_CODE = "yellow"
COLOR_EXPLAIN = "white"
COLOR_DEBUG = "grey"

def colored(text, color):
    colors = {
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m",
        "white": "\033[97m", "grey": "\033[90m",
    }
    end_color = "\033[0m"
    if sys.stdout.isatty():
        return f"{colors.get(color, '')}{text}{end_color}"
    else:
        return text

def print_header(text):
    print(colored(f"--- {text} ---", COLOR_HEADER))

def print_success(text):
    print(colored(f"[+] {text}", COLOR_SUCCESS))

def print_error(text):
    print(colored(f"[!] {text}", COLOR_ERROR), file=sys.stderr)

def print_warning(text):
    print(colored(f"[*] {text}", COLOR_WARNING))

def print_info(text):
    print(colored(f"[*] {text}", COLOR_INFO))

def print_debug(text):
    print(colored(f"[DEBUG] {text}", COLOR_DEBUG), file=sys.stderr)

def prompt_user(text):
    print(colored(f"{text}: ", COLOR_PROMPT), end='', flush=True)
    return input().strip()

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "ailconfig.json")

class AILanguageInterpreter:
    def __init__(self):
        self.config = self.load_config()
        self.provider = self.config.get("provider", None)
        self.api_keys = {
            "hf": self.config.get("hf_api_key", ""),
            "or": self.config.get("or_api_key", ""),
            "google": self.config.get("google_api_key", ""),
            "requesty": self.config.get("requesty_api_key", "")
        }
        self.model_info = self.config.get("model_info", {
            "hf": "Qwen/Qwen2.5-72B-Instruct",
            "or": "google/gemini-2.0-flash-exp:free",
            "google": "gemini-2.5-pro-exp-03-25",
            "requesty": "google/gemma-3-27b-it"
        })
        self.api_url = None
        self.headers = {}

        if not self.provider:
            self.initial_provider_setup()
        else:
            self.setup_api_config()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print_warning(f"Configuration file not found. Creating default '{CONFIG_FILE}'.")
            return self.create_default_config()
        except json.JSONDecodeError:
            print_error("Error decoding configuration file. Backing up and creating default.")
            backup_path = CONFIG_FILE + ".bak"
            try:
                shutil.copyfile(CONFIG_FILE, backup_path)
                print_warning(f"Backed up corrupted config to {backup_path}")
            except Exception as e:
                print_error(f"Could not back up corrupted config file: {e}")
            return self.create_default_config()

    def create_default_config(self):
        default_config = {
            "provider": None,
            "hf_api_key": "",
            "or_api_key": "",
            "google_api_key": "",
            "requesty_api_key": "",
            "model_info": {
                "hf": "Qwen/Qwen2.5-72B-Instruct",
                "or": "google/gemini-2.0-flash-exp:free",
                "google": "gemini-1.5-flash-latest",
                "requesty": "gpt-4"
            },
            "project_dirs": []
        }
        self.save_config(default_config)
        return default_config

    def save_config(self, config_data=None):
        if config_data is None:
            config_data = self.config
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=4)
        except IOError as e:
            print_error(f"Error saving configuration: {e}")

    def initial_provider_setup(self):
        print_header("Initial Setup: AI Provider Selection")
        print("Please choose your preferred AI provider:")
        print("1. HuggingFace (Requires API Key)")
        print("2. OpenRouter (Requires API Key)")
        print("3. Google AI (Requires API Key)")
        print("4. Requesty (Requires API Key)")
        while True:
            choice = prompt_user("Enter choice (1, 2, 3, or 4)")
            if choice == '1':
                self.provider = "hf"
                break
            elif choice == '2':
                self.provider = "or"
                break
            elif choice == '3':
                self.provider = "google"
                break
            elif choice == '4':
                self.provider = "requesty"
                break
            else:
                print_error("Invalid choice. Please enter 1, 2, 3, or 4.")
        self.config["provider"] = self.provider
        self.save_config()
        print_success(f"Provider set to '{self.provider}'.")
        self.setup_api_config()


    def setup_api_config(self):
        key_needed = False
        provider_name = ""
        key_type = ""
        self.api_url = None
        self.headers = {}

        if self.provider == "hf":
            provider_name = "HuggingFace"
            key_type = "hf"
            if not self.api_keys["hf"]: key_needed = True
        elif self.provider == "or":
            provider_name = "OpenRouter"
            key_type = "or"
            if not self.api_keys["or"]: key_needed = True
        elif self.provider == "google":
            provider_name = "Google AI"
            key_type = "google"
            if not self.api_keys["google"]: key_needed = True
        elif self.provider == "requesty":
            provider_name = "Requesty"
            key_type = "requesty"
            if not self.api_keys["requesty"]: key_needed = True
        else:
            print_warning(f"Unknown or unset provider '{self.provider}'. Please use 'provider hf/or/google/requesty'.")
            return

        if key_needed:
            print_warning(f"{provider_name} provider selected, but API key is missing.")
            api_key = prompt_user(f"Please enter your {provider_name} API key")
            self.api_keys[key_type] = api_key
            self.config[f"{key_type}_api_key"] = api_key
            self.save_config()
            print_success(f"{provider_name} API key stored.")

        if self.provider == "hf":
            if self.api_keys['hf']:
                model_name = self.model_info.get("hf", "default-hf-model")
                self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
                self.headers = {"Authorization": f"Bearer {self.api_keys['hf']}"}
            else:
                 print_error("HuggingFace API key not set. Requests will fail.")
        elif self.provider == "or":
            if self.api_keys['or']:
                self.api_url = "https://openrouter.ai/api/v1/chat/completions"
                self.headers = {
                    "Authorization": f"Bearer {self.api_keys['or']}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://ailang.interpreter",
                    "X-Title": "AI Language Interpreter"
                }
            else:
                 print_error("OpenRouter API key not set. Requests will fail.")
        elif self.provider == "google":
             if self.api_keys['google']:
                 model_name = self.model_info.get("google", "gemini-1.5-flash-latest")
                 self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                 self.headers = {"Content-Type": "application/json"}
             else:
                  print_error("Google AI API key not set. Requests will fail.")
        elif self.provider == "requesty":
             if self.api_keys['requesty']:
                 self.api_url = "https://router.requesty.ai/v1/chat/completions"
                 self.headers = {
                     "Authorization": f"Bearer {self.api_keys['requesty']}",
                     "Content-Type": "application/json"
                 }
             else:
                  print_error("Requesty API key not set. Requests will fail.")


    def change_provider(self, new_provider):
        valid_providers = ["hf", "or", "google", "requesty"]
        if new_provider not in valid_providers:
            print_error(f"Invalid provider '{new_provider}'. Use one of: {', '.join(valid_providers)}.")
            return False
        self.provider = new_provider
        self.config["provider"] = new_provider
        self.save_config()
        print_success(f"API provider changed to '{self.provider}'.")
        self.setup_api_config()
        return True

    def change_model(self):
        if not self.provider:
            print_error("Please set a provider first using 'provider <name>'.")
            return

        current_model = self.model_info.get(self.provider, "N/A")
        print_info(f"Current model for {self.provider}: {current_model}")
        new_model = prompt_user(f"Enter new model name for {self.provider} (leave blank to keep current)")

        if new_model:
            self.model_info[self.provider] = new_model
            self.config["model_info"] = self.model_info
            self.save_config()
            print_success(f"Model for {self.provider} updated to '{new_model}'.")
            self.setup_api_config()
        else:
            print_info("Model unchanged.")


    def convert_to_golang(self, english_text, project_dir):
        if not self.api_url:
             print_error("API configuration is not set up. Cannot convert.")
             raise ConnectionError("API provider/key not configured.")

        prompt = f"""You are an expert Golang developer. Convert the following English description into clean, efficient, and idiomatic Golang code. The code should:
1. Be placed within a 'main' package and have a 'main' function.
2. Follow Go best practices and conventions (e.g., proper naming, error handling).
3. Include basic error handling where appropriate (e.g., for input conversions, file operations).
4. Use appropriate standard library packages ONLY unless external libraries are explicitly requested or obviously necessary for the core task.
5. Be complete and ready to compile.

English description:
{english_text}

Generate ONLY the Golang code inside a single block, starting with ```go and ending with ```. Do not include any other text, explanations, or comments before or after the code block."""

        try:
            print_info(f"Sending request to {self.provider} for Go code generation...")
            response_text = self._dispatch_api_call(prompt, max_tokens=3000)

            match = re.search(r'```(?:go|golang)?\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
            if match:
                golang_code = match.group(1).strip()
            else:
                print_warning("Could not find ```go ... ``` block in AI response. Assuming entire response is code.")
                print_debug(f"--- AI Response Snippet ---\n{response_text[:500]}...\n--- End Snippet ---")
                golang_code = response_text.strip()
                if not ("package main" in golang_code or "func main" in golang_code):
                     print_warning("Fallback response doesn't seem like Go code. Proceeding with caution.")


            if not golang_code.lstrip().startswith("package main"):
                 if "package main" in golang_code:
                      start_index = golang_code.find("package main")
                      print_warning("Generated code didn't start with 'package main', but found it later. Adjusting.")
                      golang_code = golang_code[start_index:]
                 else:
                      print_warning("Generated code doesn't start with 'package main'. Prepending it.")
                      golang_code = "package main\n\n" + golang_code


            file_name = "main.go"
            file_path = os.path.join(project_dir, file_name)
            os.makedirs(project_dir, exist_ok=True)

            with open(file_path, "w", encoding='utf-8') as f:
                f.write(golang_code)

            print_success(f"Golang code saved to {file_path}")
            return file_path

        except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
            print_error(f"API request failed: {e}")
            self.explain_error(f"Network or API request error: {e}")
            raise
        except Exception as e:
            print_error(f"Error converting English to Golang: {e}")
            self.explain_error(f"Conversion process failed. Details: {e}")
            raise


    def debug_golang_code(self, golang_file, error_message):
        print_info(f"Attempting to debug code with {self.provider}...")
        try:
            with open(golang_file, 'r', encoding='utf-8') as f:
                current_code = f.read()

            prompt = f"""You are an expert Golang debugger. Analyze the following Golang code and the build/runtime error it produced.
Fix the error(s) in the code. Ensure the corrected code is complete, runnable, and remains within the 'main' package.
Return ONLY the complete, corrected Golang code inside a single ```go ... ``` block. Do not include explanations or comments before or after the code block.

Error Message:
```
{error_message}
```

Current Code:
```go
{current_code}
```"""

            response_text = self._dispatch_api_call(prompt, max_tokens=3000)

            match = re.search(r'```(?:go|golang)?\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
            if match:
                fixed_code = match.group(1).strip()
                if not fixed_code.lstrip().startswith("package main"):
                     print_warning("AI fix doesn't start with 'package main'. Attempting to fix.")
                     if "package main" in fixed_code:
                         start_index = fixed_code.find("package main")
                         fixed_code = fixed_code[start_index:]
                     else:
                         fixed_code = "package main\n\n" + fixed_code

                if fixed_code.strip() == current_code.strip():
                     print_warning("AI returned the same code. No fix applied.")
                     return False

                with open(golang_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                print_success("AI applied potential fixes to the code.")
                return True
            else:
                print_error("AI response for debugging did not contain a valid Go code block.")
                print_debug(f"--- AI Response Snippet ---\n{response_text[:500]}...\n--- End Snippet ---")
                self.explain_error("The AI failed to return the corrected code in the expected format during debugging.")
                return False

        except FileNotFoundError:
             print_error(f"Code file not found: {golang_file}")
             return False
        except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
            print_error(f"API request failed during debugging: {e}")
            self.explain_error(f"Network or API request error during debugging: {e}")
            return False
        except Exception as e:
            print_error(f"Error during AI debugging: {e}")
            self.explain_error(str(e))
            return False


    def infer_and_install_dependencies(self, golang_file, project_dir):
        print_info("Checking for Go dependencies...")
        try:
            try:
                subprocess.run(['go', 'version'], check=True, capture_output=True, timeout=10)
            except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                 print_error("'go' command not found or not working. Cannot manage dependencies.")
                 self.explain_error("'go' command not found or failed. Please ensure Go is installed and in your PATH.")
                 return

            go_mod_path = os.path.join(project_dir, "go.mod")
            if not os.path.exists(go_mod_path):
                 print_warning("go.mod not found. Skipping dependency check. Run 'go mod init <module_name>' first.")
                 return

            list_cmd = ["go", "list", "-f", "{{range .Imports}}{{.}}\n{{end}}{{range .TestImports}}{{.}}\n{{end}}{{range .XTestImports}}{{.}}\n{{end}}", "."]
            result = subprocess.run(list_cmd, cwd=project_dir, capture_output=True, text=True, check=True, timeout=30)
            all_imports = set(result.stdout.strip().split())

            std_lib_cmd = ["go", "list", "std"]
            result = subprocess.run(std_lib_cmd, capture_output=True, text=True, check=True, timeout=30)
            std_libs = set(result.stdout.strip().split())

            mod_name_cmd = ["go", "mod", "edit", "-json"]
            result = subprocess.run(mod_name_cmd, cwd=project_dir, capture_output=True, text=True, check=True, timeout=30)
            mod_info = json.loads(result.stdout)
            module_path = mod_info.get("Module", {}).get("Path", "")

            external_deps = []
            for imp in all_imports:
                if imp in std_libs: continue
                if module_path and (imp == module_path or imp.startswith(module_path + "/")): continue
                if imp.startswith("."): continue
                if '.' in imp.split('/')[0]:
                    external_deps.append(imp)
                else:
                    print_debug(f"Skipping potential non-external import: {imp}")


            if not external_deps:
                print_success("No external dependencies found or needed.")
                return

            print_info(f"Found potential external dependencies: {', '.join(external_deps)}")
            print_info("Attempting to install using 'go get'...")

            installed_any = False
            failed_deps = []
            for dep in external_deps:
                get_cmd = ["go", "get", dep]
                get_result = subprocess.run(get_cmd, cwd=project_dir, capture_output=True, text=True, check=False, timeout=120)
                if get_result.returncode != 0:
                    print_error(f"Failed to install '{dep}':\n{get_result.stderr}")
                    failed_deps.append(dep)
                else:
                    print_success(f"Successfully installed/updated '{dep}'.")
                    installed_any = True

            if installed_any and not failed_deps:
                print_success("All detected dependencies installed successfully.")
            elif failed_deps:
                print_error(f"Failed to install some dependencies: {', '.join(failed_deps)}")
                self.explain_error(f"Could not automatically install these libraries: {', '.join(failed_deps)}. The AI might need to remove them or use different ones, or you might need to install them manually if they exist.")

            print_info("Running 'go mod tidy' to clean up...")
            tidy_result = subprocess.run(["go", "mod", "tidy"], cwd=project_dir, capture_output=True, text=True, check=False, timeout=60)
            if tidy_result.returncode != 0:
                 print_warning(f"'go mod tidy' failed:\n{tidy_result.stderr}")
            else:
                 print_success("'go mod tidy' completed.")


        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr or e.stdout or "(no output captured)"
            print_error(f"Error checking or installing dependencies: {e}\nCommand: {' '.join(e.cmd)}\nOutput:\n{stderr_output}")
            self.explain_error(f"Failed to check or install necessary code libraries. Error: {stderr_output}")
        except subprocess.TimeoutExpired as e:
             print_error(f"Timeout during dependency check/install: Command {' '.join(e.cmd)} timed out.")
             self.explain_error(f"The process for checking or installing libraries took too long ({e.timeout}s). Check your network or the complexity of dependencies.")
        except json.JSONDecodeError as e:
             print_error(f"Error parsing go.mod information: {e}")
             self.explain_error("Could not read the project's module information (go.mod). It might be corrupted.")
        except Exception as e:
            print_error(f"An unexpected error occurred during dependency check: {e}")
            self.explain_error(f"An unexpected issue occurred while managing code libraries: {e}")


    def build_program(self, golang_file, project_dir):
        print_info(f"Building {os.path.basename(golang_file)}...")
        build_cmd = ["go", "build", "."]
        try:
            try:
                subprocess.run(['go', 'version'], check=True, capture_output=True, timeout=10)
            except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                 print_error("'go' command not found or not working. Cannot build.")
                 self.explain_error("'go' command not found or failed. Please ensure Go is installed and in your PATH.")
                 return False, "'go' command not found or failed."

            result = subprocess.run(build_cmd, cwd=project_dir, capture_output=True, text=True, check=False, timeout=60)

            if result.returncode != 0:
                print_error("Build failed!")
                stderr_output = result.stderr or "(No error message from compiler)"
                print(colored("--- Compiler Error ---", COLOR_ERROR))
                print(colored(stderr_output, COLOR_ERROR))
                print(colored("--- End Compiler Error ---", COLOR_ERROR))
                return False, stderr_output
            else:
                print_success("Build successful!")
                exe_name = Path(project_dir).name
                if sys.platform == 'win32': exe_name += ".exe"
                exe_path = os.path.join(project_dir, exe_name)
                if not os.path.exists(exe_path):
                    go_file_base = Path(golang_file).stem
                    fallback_exe_name = go_file_base
                    if sys.platform == 'win32': fallback_exe_name += ".exe"
                    fallback_exe_path = os.path.join(project_dir, fallback_exe_name)
                    if os.path.exists(fallback_exe_path):
                        print_warning(f"Executable found as '{fallback_exe_name}', not '{exe_name}'.")
                        exe_path = fallback_exe_path
                    else:
                        final_fallback_name = "main.exe" if sys.platform == 'win32' else "main"
                        final_fallback_path = os.path.join(project_dir, final_fallback_name)
                        if os.path.exists(final_fallback_path):
                             print_warning(f"Executable found as '{final_fallback_name}', not '{exe_name}'.")
                             exe_path = final_fallback_path
                        else:
                             print_warning(f"Build reported success, but could not find executable named '{exe_name}', '{fallback_exe_name}', or '{final_fallback_name}'.")
                             return True, ""

                print_success(f"Executable created: {exe_path}")
                return True, ""

        except subprocess.TimeoutExpired:
             print_error("Build timed out after 60 seconds.")
             return False, "Build process timed out."
        except Exception as e:
             print_error(f"An unexpected error occurred during build: {e}")
             return False, f"Unexpected build error: {e}"


    def show_interactive_commands(self):
        print_header("Interactive Mode Commands")
        print(colored("show     ", COLOR_INFO) + "- Display current code")
        print(colored("modify   ", COLOR_INFO) + "- Make specific changes to the code (describe the change)")
        print(colored("explain  ", COLOR_INFO) + "- Explain the current code")
        print(colored("ev       ", COLOR_INFO) + "- Explain the current code VISUALLY (generates flowchart.png)")
        print(colored("optimize ", COLOR_INFO) + "- Optimize the current code (describe focus)")
        print(colored("add      ", COLOR_INFO) + "- Add new functionality (describe feature)")
        print(colored("build    ", COLOR_INFO) + "- Try to build the current code")
        print(colored("run      ", COLOR_INFO) + "- Try to build and run the current code")
        print(colored("help     ", COLOR_INFO) + "- Show this command list")
        print(colored("done     ", COLOR_INFO) + "- Exit interactive mode (will attempt final build)")


    def interactive_session(self, source_input):
        project_dir = None
        golang_file = None
        english_text = None
        source_name = "template_project"

        try:
            if isinstance(source_input, str) and source_input.endswith('.ail') and os.path.exists(source_input):
                ail_file_path = source_input
                source_name = Path(ail_file_path).stem
                print_info(f"Starting interactive mode with file: {ail_file_path}")
                with open(ail_file_path, 'r', encoding='utf-8') as f:
                    english_text = f.read()
            elif isinstance(source_input, str):
                english_text = source_input
                first_line = english_text.split('\n')[0]
                source_name = ''.join(filter(str.isalnum, first_line.replace(" ", "_")))[:30] or "template_project"
                print_info(f"Starting interactive mode with selected template '{source_name}'.")
            else:
                print_error("Invalid input for interactive session.")
                return

            if not english_text:
                 print_error("No description provided (empty file or template).")
                 return

            default_project_name = re.sub(r'[^\w\-_\.]', '_', source_name)
            project_name_input = prompt_user(f"Enter the name for your project (default: {default_project_name})")
            project_name = project_name_input if project_name_input else default_project_name
            project_name = re.sub(r'[^\w\-_\.]', '_', project_name)

            project_dir = os.path.join(os.getcwd(), project_name)
            os.makedirs(project_dir, exist_ok=True)
            print_info(f"Project directory: {project_dir}")

            if "project_dirs" not in self.config: self.config["project_dirs"] = []
            abs_project_dir = os.path.abspath(project_dir)
            if abs_project_dir not in self.config["project_dirs"]:
                self.config["project_dirs"].append(abs_project_dir)
                self.save_config()

            print_info("Converting description to Golang...")
            golang_file = self.convert_to_golang(english_text, project_dir)

            go_mod_path = os.path.join(project_dir, "go.mod")
            if not os.path.exists(go_mod_path):
                print_info("Initializing Go module...")
                module_path_name = project_name.lower().replace('_', '-')
                try:
                    subprocess.run(['go', 'version'], check=True, capture_output=True, timeout=10)
                    mod_init_result = subprocess.run(["go", "mod", "init", module_path_name], cwd=project_dir, capture_output=True, text=True, check=False, timeout=30)
                    if mod_init_result.returncode != 0:
                         if "already exists" in mod_init_result.stderr:
                              print_success("go.mod already exists.")
                         else:
                              print_warning(f"'go mod init' failed. Dependency management might not work correctly.\nError: {mod_init_result.stderr}")
                    else:
                         print_success(f"'go mod init {module_path_name}' successful.")
                except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                     print_error("'go' command not found or not working. Cannot initialize module.")
                     self.explain_error("'go' command not found or failed. Please ensure Go is installed and in your PATH.")
                     print_warning("Proceeding without Go module initialization.")
                except Exception as e:
                     print_error(f"Unexpected error during 'go mod init': {e}")
            else:
                 print_success("go.mod already exists.")

            self.infer_and_install_dependencies(golang_file, project_dir)

            self.show_interactive_commands()

            while True:
                interactive_prompt = colored(f"[{project_name}] >> ", COLOR_PROMPT)
                command_input = input(interactive_prompt).strip()
                parts = command_input.split(maxsplit=1)
                command = parts[0].lower() if parts else ""
                args = parts[1] if len(parts) > 1 else ""

                if command == 'done':
                    self.build_and_debug_on_exit(golang_file, project_dir)
                    break
                elif command == 'show':
                    try:
                        with open(golang_file, 'r', encoding='utf-8') as f:
                            print(colored("--- Current Code ---", COLOR_HEADER))
                            print(colored(f.read(), COLOR_CODE))
                            print(colored("--- End Code ---", COLOR_HEADER))
                    except Exception as e:
                         print_error(f"Error reading code file: {e}")
                elif command == 'help':
                    self.show_interactive_commands()
                elif command == 'ev':
                    self.explain_visually(golang_file, project_dir)
                elif command == 'explain':
                    self.handle_interactive_command(command, golang_file, "")
                elif command in ['modify', 'optimize', 'add']:
                    user_input = prompt_user(f"Describe the task for '{command}'")
                    if not user_input:
                         print_warning("No description provided. Aborting command.")
                         continue
                    if self.handle_interactive_command(command, golang_file, user_input):
                        print_info("Code modified by AI. Checking dependencies and attempting build...")
                        self.infer_and_install_dependencies(golang_file, project_dir)
                        self.attempt_build(golang_file, project_dir, offer_debug=True)
                    else:
                        print_info("Code modification failed or was aborted. Skipping build check.")
                elif command == 'build':
                     self.attempt_build(golang_file, project_dir, offer_debug=True)
                elif command == 'run':
                     self.attempt_run(golang_file, project_dir)
                elif not command:
                     continue
                else:
                    print_error(f"Unknown command: '{command}'. Type 'help' to see available commands.")

        except FileNotFoundError as e:
             print_error(f"Required file not found: {e}")
             self.explain_error(str(e))
        except (ConnectionError, TimeoutError) as e:
             print_error(f"API Error: {e}")
             print_warning("Please check your API key, provider settings, and internet connection.")
        except KeyboardInterrupt:
             print_warning("\nInteractive session interrupted by user.")
        except Exception as e:
            print_error(f"An unexpected error occurred in the interactive session: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.explain_error(f"Unexpected session error: {e}")
            except Exception as explain_e:
                 print_error(f"Additionally, failed to explain the error: {explain_e}")
        finally:
            print_info("Exiting interactive mode.")


    def attempt_build(self, golang_file, project_dir, offer_debug=False):
        print_info(f"Attempting to build {os.path.basename(golang_file)}...")
        success, error_msg = self.build_program(golang_file, project_dir)

        if not success:
            if offer_debug:
                debug_choice = prompt_user("Build failed. Would you like the AI to try and fix this? (y/n)").lower()
                if debug_choice == 'y':
                    if self.debug_golang_code(golang_file, error_msg):
                         print_info("AI attempted fixes. Dependencies might have changed, re-checking...")
                         self.infer_and_install_dependencies(golang_file, project_dir)
                         print_success("Dependencies checked. Try building again.")
                         return False
                    else:
                         print_error("AI debugging failed or made no changes.")
                         return False
                else:
                    self.explain_error(error_msg)
                    return False
            else:
                self.explain_error(error_msg)
                return False
        else:
            return True

    def attempt_run(self, golang_file, project_dir):
        if not self.attempt_build(golang_file, project_dir, offer_debug=True):
             print_error("Build failed or was aborted, cannot run program.")
             return

        exe_name = Path(project_dir).name
        if sys.platform == 'win32': exe_name += ".exe"
        exe_path = os.path.join(project_dir, exe_name)

        if not os.path.exists(exe_path):
            go_file_base = Path(golang_file).stem
            fallback_exe_name = go_file_base
            if sys.platform == 'win32': fallback_exe_name += ".exe"
            fallback_exe_path = os.path.join(project_dir, fallback_exe_name)
            if os.path.exists(fallback_exe_path):
                exe_path = fallback_exe_path
            else:
                final_fallback_name = "main.exe" if sys.platform == 'win32' else "main"
                final_fallback_path = os.path.join(project_dir, final_fallback_name)
                if os.path.exists(final_fallback_path):
                    exe_path = final_fallback_path
                else:
                    print_warning(f"Could not find executable after successful build. Trying 'go run .'.")
                    try:
                        subprocess.run(['go', 'version'], check=True, capture_output=True, timeout=10)
                        print_info("Running program with 'go run .'...")
                        run_result = subprocess.run(["go", "run", "."], cwd=project_dir, check=False, text=True, timeout=300)
                        if run_result.returncode != 0:
                            print_warning(f"Program exited with error (code {run_result.returncode}) (via go run).")
                        else:
                            print_success("Program finished (via go run).")
                    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                        print_error(f"'go run .' failed: {e}")
                        self.explain_error(f"'go run .' command failed. Ensure Go is installed and the code is runnable. Error: {e}")
                    except Exception as e:
                        print_error(f"Error running program with 'go run': {e}")
                    return

        print_info(f"Running executable: '{exe_path}'...")
        try:
            if not os.path.isabs(exe_path):
                exe_path = os.path.join(project_dir, os.path.basename(exe_path))

            run_cmd = [exe_path]
            run_result = subprocess.run(run_cmd, cwd=project_dir, check=False, timeout=300)

            if run_result.returncode != 0:
                 print_warning(f"Program exited with status code {run_result.returncode}.")
            else:
                 print_success("Program finished.")

        except FileNotFoundError:
             print_error(f"Executable not found at '{exe_path}' despite earlier checks. Build might be inconsistent.")
             self.explain_error(f"Could not find the program file ('{os.path.basename(exe_path)}') to run, even though it seemed to build correctly.")
        except PermissionError:
             print_error(f"Permission denied to execute '{exe_path}'. Check file permissions (e.g., chmod +x).")
             self.explain_error(f"Cannot run the program due to file permissions. You might need to grant execute permission.")
        except subprocess.TimeoutExpired:
             print_error(f"Program timed out after 300 seconds.")
             self.explain_error("The program took too long to run and was stopped.")
        except Exception as e:
             print_error(f"Error running program: {e}")
             self.explain_error(f"An error occurred while trying to run the compiled program: {e}")


    def explain_visually(self, golang_file, project_dir):
        try:
            subprocess.run(['dot', '-V'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print_error("Graphviz 'dot' command not found or not working.")
            print_warning("Please install Graphviz (from https://graphviz.org/download/) and ensure 'dot' is in your system's PATH.")
            self.explain_error("Graphviz software ('dot' command) is needed for visual explanation, but it wasn't found or failed to run. Please install it.")
            return
        except Exception as e:
             print_error(f"Unexpected error checking for Graphviz: {e}")
             return

        print_info(f"Generating visual explanation (flowchart) using {self.provider}...")
        try:
            with open(golang_file, 'r', encoding='utf-8') as f:
                current_code = f.read()

            prompt = f"""Analyze the following Go code. Generate a flowchart representation of its main logic using the DOT language format suitable for Graphviz.

Focus on the sequence of operations, loops (for), and conditional branches (if/else, switch) in the `main` function primarily. Keep the node labels concise (e.g., "Read input", "Calculate result", "Check error"). Use standard DOT syntax.

Example DOT output format:
```dot
digraph G {{
  rankdir=TB;
  node [shape=box, style=rounded, fontname="Arial"];
  edge [fontname="Arial"];

  start [label="Start", shape=ellipse];
  read_input [label="Read Input"];
  process_data [label="Process Data"];
  check_condition [label="Is Condition Met?", shape=diamond];
  action_true [label="Do Action A"];
  action_false [label="Do Action B"];
  end [label="End", shape=ellipse];

  start -> read_input;
  read_input -> process_data;
  process_data -> check_condition;
  check_condition -> action_true [label=" Yes"];
  check_condition -> action_false [label=" No"];
  action_true -> end;
  action_false -> end;
}}
```

Go Code:
```go
{current_code}
```

Generate ONLY the DOT language code block, starting with ```dot or digraph and ending with ``` or }}. Do not include any other text, explanations, or markdown formatting around the DOT code itself."""

            print_info("Sending request to AI for DOT language generation...")
            dot_code = self._dispatch_api_call(prompt, max_tokens=1500)

            dot_code = re.sub(r'^```(?:dot)?\s*', '', dot_code, flags=re.MULTILINE)
            dot_code = re.sub(r'\s*```$', '', dot_code, flags=re.MULTILINE)
            dot_code = dot_code.strip()

            if not dot_code.startswith('digraph'):
                print_error("AI did not return valid DOT language starting with 'digraph'.")
                print_debug(f"--- AI Response Snippet ---\n{dot_code[:500]}...\n--- End Snippet ---")
                self.explain_error("The AI failed to generate the flowchart data in the expected format (DOT language).")
                return

            output_filename = 'flowchart'
            output_path_base = os.path.join(project_dir, output_filename)
            dot_file_path = output_path_base + ".dot"
            png_file_path = output_path_base + ".png"

            print_info(f"Received DOT data. Rendering graph to {png_file_path}...")

            try:
                with open(dot_file_path, 'w', encoding='utf-8') as dot_f:
                    dot_f.write(dot_code)
                print_debug(f"DOT code saved to {dot_file_path}")

                os.makedirs(project_dir, exist_ok=True)
                src = graphviz.Source(dot_code, filename=dot_file_path, format='png', engine='dot')
                rendered_path = src.render(directory=project_dir, view=False, cleanup=True)

                expected_png_path = os.path.join(project_dir, Path(dot_file_path).stem + '.gv.png')
                final_png_path = os.path.join(project_dir, Path(dot_file_path).stem + '.png')

                if os.path.exists(rendered_path):
                     if rendered_path.endswith('.gv.png') and not os.path.exists(final_png_path):
                         try:
                             shutil.move(rendered_path, final_png_path)
                             print_success(f"Flowchart saved successfully: {final_png_path}")
                         except OSError as move_err:
                             print_error(f"Could not rename flowchart file: {move_err}")
                             print_warning(f"Flowchart may be at: {rendered_path}")
                     else:
                         print_success(f"Flowchart saved successfully: {rendered_path}")
                elif os.path.exists(final_png_path):
                     print_success(f"Flowchart saved successfully: {final_png_path}")
                else:
                     print_error(f"Graphviz rendering finished, but output file '{final_png_path}' (or variations) not found.")
                     self.explain_error("Graphviz seemed to run, but the final flowchart image was not created. The DOT data might still be invalid.")
                     print_warning(f"Problematic DOT code saved to: {dot_file_path}")


            except graphviz.backend.execute.ExecutableNotFound:
                 print_error("Graphviz executable ('dot') not found by the library.")
                 self.explain_error("Graphviz software ('dot' command) not found.")
            except subprocess.CalledProcessError as cpe:
                 error_output = cpe.stderr.decode('utf-8', errors='ignore') if cpe.stderr else "No error output captured."
                 print_error(f"Error during Graphviz rendering (DOT syntax likely invalid):\n{error_output}")
                 print_warning(f"Problematic DOT code saved to: {dot_file_path}")
                 self.explain_error(f"Graphviz failed to process the flowchart data generated by the AI (saved in {output_filename}.dot). Error: {error_output}")
            except Exception as e:
                 print_error(f"An unexpected error occurred during flowchart rendering: {e}")
                 self.explain_error(f"Failed to create the flowchart image. Details: {e}")
                 if os.path.exists(dot_file_path):
                     print_warning(f"Problematic DOT code saved to: {dot_file_path}")


        except FileNotFoundError:
            print_error(f"Code file not found: {golang_file}")
        except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
            print_error(f"API request failed while generating flowchart data: {e}")
            self.explain_error(f"Network or API request error during flowchart generation: {e}")
        except Exception as e:
            print_error(f"Error generating visual explanation: {e}")
            self.explain_error(str(e))


    def build_and_debug_on_exit(self, golang_file, project_dir):
        print_info("Attempting final build before exiting...")
        success, error_msg = self.build_program(golang_file, project_dir)
        if not success:
            print_error("Final build failed.")
            debug_choice = prompt_user("Would you like the AI to try and fix the final build errors? (y/n)").lower()
            if debug_choice == 'y':
                if self.debug_golang_code(golang_file, error_msg):
                    print_info("AI attempted fixes. Re-checking dependencies...")
                    self.infer_and_install_dependencies(golang_file, project_dir)
                    print_info("Trying one last build...")
                    success, final_error_msg = self.build_program(golang_file, project_dir)
                    if success:
                        print_success("Final build successful after AI fixes!")
                    else:
                        print_error("Build still failed after AI fixes.")
                        self.explain_error(final_error_msg)
                else:
                    print_error("AI debugging failed or made no changes.")
                    self.explain_error(error_msg)
            else:
                 self.explain_error(error_msg)
        else:
            print_success("Final build successful.")


    def handle_interactive_command(self, command, golang_file, user_input):
        try:
            with open(golang_file, 'r', encoding='utf-8') as f:
                current_code = f.read()

            prompt = ""
            is_code_modification = command in ['modify', 'optimize', 'add']

            if command == 'explain':
                prompt = f"""Explain the following Golang code step-by-step in simple terms suitable for a beginner. Focus on what the program does, the purpose of major functions or blocks, and the overall flow.

```go
{current_code}
```

Provide only the explanation text, formatted clearly."""
            elif is_code_modification:
                if not user_input:
                     print_warning("No description provided for command. Aborting.")
                     return False

                prompt_templates = {
                    'modify': f"""You are an expert Golang developer. Modify the following Golang code based *strictly* on the user's request.
Ensure the code remains complete, runnable, and within the 'main' package.
Return ONLY the complete, modified Golang code inside a single ```go ... ``` block. Do not add comments explaining your changes within the code block.

User request: '{user_input}'

Current Code:
```go
{current_code}
```""",
                    'optimize': f"""You are an expert Golang performance and style optimizer. Optimize the following Golang code, focusing *specifically* on the aspect described by the user (e.g., speed, memory usage, readability, concurrency).
If the user request is vague, prioritize readability and standard Go idioms.
Return ONLY the complete, optimized Golang code inside a single ```go ... ``` block. Do not add comments explaining your changes within the code block.

User focus: '{user_input}'

Current Code:
```go
{current_code}
```""",
                    'add': f"""You are an expert Golang developer. Add the new functionality described by the user to the following Golang code.
Integrate the new feature smoothly into the existing structure. Ensure the code remains complete, runnable, and within the 'main' package.
Return ONLY the complete, modified Golang code inside a single ```go ... ``` block. Do not add comments explaining your changes within the code block.

User request to add: '{user_input}'

Current Code:
```go
{current_code}
```"""
                }
                prompt = prompt_templates[command]
            else:
                print_error(f"Internal error: Unknown command '{command}' in handle_interactive_command.")
                return False

            print_info(f"Sending request to {self.provider} for '{command}' task...")
            max_tokens = 3500 if is_code_modification else 1000
            response_text = self._dispatch_api_call(prompt, max_tokens=max_tokens)


            if command == 'explain':
                print_header("AI Explanation")
                print(colored(response_text, COLOR_EXPLAIN))
                print(colored("--- End Explanation ---", COLOR_HEADER))
                return True
            else:
                match = re.search(r'```(?:go|golang)?\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
                if match:
                    modified_code = match.group(1).strip()
                    if not modified_code.lstrip().startswith("package main"):
                         print_warning("AI response for modification doesn't start with 'package main'. Attempting to fix.")
                         if "package main" in modified_code:
                              start_index = modified_code.find("package main")
                              modified_code = modified_code[start_index:]
                         else:
                              modified_code = "package main\n\n" + modified_code

                    if modified_code.strip() == current_code.strip():
                         print_warning("AI returned the same code. No changes applied.")
                         return False

                    with open(golang_file, 'w', encoding='utf-8') as f:
                        f.write(modified_code)
                    print_success(f"Code '{command}' operation successful!")
                    return True
                else:
                    print_error(f"AI response for '{command}' did not contain a valid Go code block (```go...```).")
                    print_debug(f"--- AI Response Snippet ---\n{response_text[:500]}...\n--- End Snippet ---")
                    self.explain_error(f"The AI failed to return the modified code in the expected format for the '{command}' command.")
                    return False

        except FileNotFoundError:
             print_error(f"Code file not found: {golang_file}")
             return False
        except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
            print_error(f"API request failed during interactive command '{command}': {e}")
            self.explain_error(f"Network or API request error during '{command}': {e}")
            return False
        except Exception as e:
            print_error(f"Error during interactive command '{command}': {str(e)}")
            self.explain_error(str(e))
            return False

    def _dispatch_api_call(self, prompt, max_tokens=2048):
        if self.provider == "hf":
            return self.send_to_hf(prompt, max_tokens=max_tokens)
        elif self.provider == "or":
            return self.send_to_or(prompt, max_tokens=max_tokens)
        elif self.provider == "google":
            return self.send_to_google(prompt, max_tokens=max_tokens)
        elif self.provider == "requesty":
            return self.send_to_requesty(prompt, max_tokens=max_tokens)
        else:
            raise ValueError(f"Unsupported or unconfigured provider: {self.provider}")

    def send_to_hf(self, prompt, max_tokens=2048):
        if not self.api_url or not self.headers.get("Authorization") or not self.api_keys.get("hf"):
             raise ConnectionError("HuggingFace API URL or Key not configured.")

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.6,
                "top_p": 0.95,
                "return_full_text": False,
                "do_sample": True,
                "use_cache": False
            },
            "options": {"wait_for_model": True}
        }
        print_debug(f"HF Payload (excluding prompt): {payload['parameters']}")

        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()

            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                return result[0]["generated_text"]
            elif isinstance(result, dict) and 'error' in result:
                 error_msg = result['error']
                 if 'estimated_time' in result: error_msg += f" (Model loading est: {result['estimated_time']:.1f}s)"
                 raise ConnectionError(f"HuggingFace API Error: {error_msg}")
            else:
                 print_warning(f"Unexpected HuggingFace response format: {result}")
                 if isinstance(result, dict) and 'generated_text' in result:
                     return result['generated_text']
                 raise Exception(f"Unexpected HuggingFace response format: {result}")

        except requests.exceptions.Timeout: raise TimeoutError("HuggingFace API request timed out.")
        except requests.exceptions.HTTPError as e: raise ConnectionError(f"HuggingFace API request failed ({e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e: raise ConnectionError(f"HuggingFace API request failed: {e}")


    def send_to_or(self, prompt, max_tokens=2048):
        if not self.api_url or not self.headers.get("Authorization") or not self.api_keys.get("or"):
             raise ConnectionError("OpenRouter API URL or Key not configured.")

        model_name = self.model_info.get("or")
        if not model_name: raise ValueError("OpenRouter model name not found in config.")

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are an expert Golang developer assistant. Respond concisely and accurately, focusing on generating or modifying Go code as requested. When asked to generate or modify code, return ONLY the complete Go code within a single ```go ... ``` block."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.6,
            "max_tokens": max_tokens,
        }
        print_debug(f"OR Payload (excluding messages): {{'model': '{model_name}', 'temperature': 0.6, 'max_tokens': {max_tokens}}}")

        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0 and \
               "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                return result["choices"][0]["message"]["content"]
            elif "error" in result:
                 error_info = result['error']
                 msg = error_info.get('message', str(error_info)) if isinstance(error_info, dict) else str(error_info)
                 raise ConnectionError(f"OpenRouter API Error: {msg}")
            else:
                 raise Exception(f"Unexpected OpenRouter response format: {result}")

        except requests.exceptions.Timeout: raise TimeoutError("OpenRouter API request timed out.")
        except requests.exceptions.HTTPError as e: raise ConnectionError(f"OpenRouter API request failed ({e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e: raise ConnectionError(f"OpenRouter API request failed: {e}")


    def send_to_google(self, prompt, max_tokens=2048):
        if not self.api_url or not self.api_keys.get("google"):
            raise ConnectionError("Google AI API URL or Key not configured.")

        api_key = self.api_keys["google"]
        url_with_key = f"{self.api_url}?key={api_key}"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.6,
                "topP": 0.95,
                "maxOutputTokens": max_tokens,
                "stopSequences": []
            },
        }
        print_debug(f"Google Payload (excluding prompt): {payload['generationConfig']}")

        try:
            response = requests.post(url_with_key, headers=self.headers, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()

            if "candidates" in result and len(result["candidates"]) > 0 and \
               "content" in result["candidates"][0] and \
               "parts" in result["candidates"][0]["content"] and len(result["candidates"][0]["content"]["parts"]) > 0 and \
               "text" in result["candidates"][0]["content"]["parts"][0]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            elif "error" in result:
                error_info = result['error']
                msg = error_info.get('message', str(error_info)) if isinstance(error_info, dict) else str(error_info)
                raise ConnectionError(f"Google AI API Error: {msg}")
            else:
                if "promptFeedback" in result and "blockReason" in result["promptFeedback"]:
                     reason = result["promptFeedback"]["blockReason"]
                     details = result["promptFeedback"].get("blockReasonMessage", "")
                     raise ConnectionError(f"Google AI request blocked. Reason: {reason}. {details}")
                raise Exception(f"Unexpected Google AI response format: {result}")

        except requests.exceptions.Timeout: raise TimeoutError("Google AI API request timed out.")
        except requests.exceptions.HTTPError as e: raise ConnectionError(f"Google AI API request failed ({e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e: raise ConnectionError(f"Google AI API request failed: {e}")


    def send_to_requesty(self, prompt, max_tokens=2048):
        if not self.api_url or not self.headers.get("Authorization") or not self.api_keys.get("requesty"):
             raise ConnectionError("Requesty API URL or Key not configured.")

        model_name = self.model_info.get("requesty")
        if not model_name: raise ValueError("Requesty model name not found in config.")

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are an expert Golang developer assistant. Respond concisely and accurately, focusing on generating or modifying Go code as requested. When asked to generate or modify code, return ONLY the complete Go code within a single ```go ... ``` block."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.6,
            "max_tokens": max_tokens,
        }
        print_debug(f"Requesty Payload (excluding messages): {{'model': '{model_name}', 'temperature': 0.6, 'max_tokens': {max_tokens}}}")

        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0 and \
               "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
                return result["choices"][0]["message"]["content"]
            elif "error" in result:
                 error_info = result['error']
                 msg = error_info.get('message', str(error_info)) if isinstance(error_info, dict) else str(error_info)
                 raise ConnectionError(f"Requesty API Error: {msg}")
            else:
                 raise Exception(f"Unexpected Requesty response format: {result}")

        except requests.exceptions.Timeout: raise TimeoutError("Requesty API request timed out.")
        except requests.exceptions.HTTPError as e: raise ConnectionError(f"Requesty API request failed ({e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e: raise ConnectionError(f"Requesty API request failed: {e}")


    def process_file(self, ail_file):
        if not ail_file.endswith('.ail'):
            print_error("Input file must have .ail extension")
            return
        if not os.path.exists(ail_file):
             print_error(f"Input file not found: {ail_file}")
             return

        print_header(f"Processing File: {os.path.basename(ail_file)}")
        project_dir = None

        try:
            with open(ail_file, 'r', encoding='utf-8') as f:
                english_text = f.read()

            project_name = Path(ail_file).stem
            project_name = re.sub(r'[^\w\-_\.]', '_', project_name)
            project_dir = os.path.join(os.getcwd(), project_name)
            os.makedirs(project_dir, exist_ok=True)
            print_info(f"Project directory: {project_dir}")

            if "project_dirs" not in self.config: self.config["project_dirs"] = []
            abs_project_dir = os.path.abspath(project_dir)
            if abs_project_dir not in self.config["project_dirs"]:
                self.config["project_dirs"].append(abs_project_dir)
                self.save_config()

            print_info("1. Converting English to Golang...")
            golang_file = self.convert_to_golang(english_text, project_dir)

            go_mod_path = os.path.join(project_dir, "go.mod")
            if not os.path.exists(go_mod_path):
                print_info("2. Initializing Go module...")
                module_path_name = project_name.lower().replace('_', '-')
                try:
                    subprocess.run(['go', 'version'], check=True, capture_output=True, timeout=10)
                    mod_init_result = subprocess.run(["go", "mod", "init", module_path_name], cwd=project_dir, capture_output=True, text=True, check=False, timeout=30)
                    if mod_init_result.returncode != 0 and "already exists" not in mod_init_result.stderr:
                         print_warning(f"'go mod init' failed.\nError: {mod_init_result.stderr}")
                    else:
                         print_success(f"Go module initialized or already exists ('{module_path_name}').")
                except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                     print_error("'go' command not found or not working. Cannot initialize module.")
                     self.explain_error("'go' command not found or failed. Please ensure Go is installed and in your PATH.")
                     print_warning("Proceeding without Go module initialization.")
                except Exception as e:
                     print_error(f"Unexpected error during 'go mod init': {e}")
            else:
                 print_success("2. Go module (go.mod) already exists.")

            print_info("3. Installing dependencies...")
            self.infer_and_install_dependencies(golang_file, project_dir)

            print_info("4. Building and Debugging...")
            max_debug_attempts = 3
            build_successful = False
            for attempt in range(max_debug_attempts):
                print_info(f"Build attempt {attempt + 1}/{max_debug_attempts}...")
                success, error_msg = self.build_program(golang_file, project_dir)
                if success:
                    build_successful = True
                    break
                else:
                    print_error("Build failed.")
                    self.explain_error(error_msg)
                    if attempt < max_debug_attempts - 1:
                        print_info("Attempting AI fix...")
                        if not self.debug_golang_code(golang_file, error_msg):
                            print_error("AI could not fix the code or returned the same code. Stopping build attempts.")
                            break
                        else:
                             print_info("Code potentially fixed by AI. Re-checking dependencies...")
                             self.infer_and_install_dependencies(golang_file, project_dir)
                    else:
                        print_error(f"Max build attempts ({max_debug_attempts}) reached. Build failed.")

            if not build_successful:
                 print_error("Could not achieve a successful build after multiple attempts.")
            else:
                 print_success("Processing complete. Final build successful.")


        except FileNotFoundError as e:
             print_error(f"Required file not found: {e}")
             self.explain_error(str(e))
        except (ConnectionError, TimeoutError) as e:
             print_error(f"API Error during processing: {e}")
        except Exception as e:
            print_error(f"An unexpected error occurred during processing: {e}")
            import traceback
            traceback.print_exc()
            self.explain_error(f"Unexpected processing error: {e}")


    def clean_files(self):
        print_header("Cleaning Generated Project Files")
        project_dirs = self.config.get("project_dirs", [])
        if not project_dirs:
            print_info("No project directories found in configuration to clean.")
            return

        cleaned_dirs_successfully = []
        failed_dirs = []
        dirs_not_found = []

        for proj_dir in list(project_dirs):
            abs_proj_dir = os.path.abspath(proj_dir)
            if os.path.isdir(abs_proj_dir):
                try:
                    shutil.rmtree(abs_proj_dir)
                    print_success(f"Removed: {abs_proj_dir}")
                    cleaned_dirs_successfully.append(proj_dir)
                    if proj_dir in self.config["project_dirs"]:
                        self.config["project_dirs"].remove(proj_dir)
                except OSError as e:
                    print_error(f"Error removing directory {abs_proj_dir}: {e}")
                    failed_dirs.append(proj_dir)
            elif os.path.exists(abs_proj_dir):
                 print_warning(f"Skipping (is a file, not a directory): {abs_proj_dir}")
                 failed_dirs.append(proj_dir)
            else:
                print_debug(f"Skipping (already removed or never existed): {abs_proj_dir}")
                dirs_not_found.append(proj_dir)
                if proj_dir in self.config["project_dirs"]:
                    self.config["project_dirs"].remove(proj_dir)

        self.save_config()

        if failed_dirs:
            print_warning(f"Some directories could not be removed: {', '.join(failed_dirs)}")
        if cleaned_dirs_successfully:
             print_success(f"Successfully cleaned {len(cleaned_dirs_successfully)} project director(y/ies).")
        if not failed_dirs and not cleaned_dirs_successfully:
             print_info("No existing project directories needed cleaning.")


    def explain_error(self, error_message):
        if not error_message or not str(error_message).strip():
             print_debug("Skipping AI explanation for empty error message.")
             return

        error_message_str = str(error_message)[:1500]

        if not self.provider or not self.api_url:
            print_warning("Cannot get AI explanation: AI provider not fully configured.")
            print(colored("--- Original Error ---", COLOR_ERROR))
            print(colored(error_message_str, COLOR_ERROR))
            print(colored("--- End Explanation ---", COLOR_HEADER))
            return

        prompt = f"""You are an expert programmer explaining errors to a beginner who doesn't know how to code.
Explain the following error message in 2-3 simple sentences. Avoid technical jargon where possible.
Focus on the likely *cause* of the problem in plain English.
Suggest 1-2 concrete things the user could try next (e.g., "try describing the task differently", "check if the file exists", "make sure the Go tools are installed", "ask the AI to use simpler code").
Do not mention specific file names like 'main.go' or line numbers unless they are part of the original error message itself. Start your explanation directly.
Output only the explanation text.

ERROR MESSAGE:
```
{error_message_str}
```
"""
        try:
            print_header("AI Error Explanation")
            explanation = self._dispatch_api_call(prompt, max_tokens=350)
            print(colored(explanation, COLOR_EXPLAIN))

        except (ConnectionError, TimeoutError) as e:
             print_error(f"Could not get AI explanation for the error: {e}")
             print(colored("--- Original Error ---", COLOR_ERROR))
             print(colored(error_message_str, COLOR_ERROR))
        except Exception as e:
             print_error(f"An unexpected error occurred while trying to explain the previous error: {e}")
             print(colored("--- Original Error ---", COLOR_ERROR))
             print(colored(error_message_str, COLOR_ERROR))
        finally:
             print(colored("--- End Explanation ---", COLOR_HEADER))


def main():
    interpreter = AILanguageInterpreter()

    if not interpreter.provider or not interpreter.api_url:
         print_warning("AI provider or API key seems missing/invalid.")
         print_info("Use 'provider <name>' and 'config <name> <key>' commands to set up.")
         print_info("Available providers: hf, or, google, requesty")

    while True:
        try:
            try:
                cwd = os.getcwd()
                cwd_name = Path(cwd).name
            except FileNotFoundError:
                cwd = SCRIPT_DIR
                cwd_name = Path(cwd).name
                print_warning(f"Current working directory invalid. Using script directory: {cwd}")
                try:
                    os.chdir(cwd)
                except OSError:
                    print_error("Cannot change to script directory. Exiting.")
                    break

            provider_str = interpreter.provider or "None"
            model_str = interpreter.model_info.get(interpreter.provider, "N/A") if interpreter.provider else "N/A"
            prompt_line1 = colored(f"AILang v{APP_VERSION}", COLOR_INFO)
            prompt_line2 = colored(f"Provider: {provider_str} | Model: {model_str} | CWD: {cwd_name}", COLOR_DEBUG)
            prompt_input_marker = colored(" $ ", COLOR_PROMPT)
            # Removed the leading '\n' here
            full_prompt = f"{prompt_line1}\n{prompt_line2}{prompt_input_marker}"

            command_input = input(full_prompt)
            command = command_input.strip()

            if not command: continue

            parts = command.split(maxsplit=1)
            base_cmd = parts[0].lower()
            args = parts[1].strip() if len(parts) > 1 else ""

            if base_cmd == 'exit':
                print_info("Exiting AI Language Interpreter.")
                break

            elif base_cmd == 'help':
                 print_header("AI Language Interpreter Help")
                 print(colored("Core Commands:", COLOR_PROMPT))
                 print(f"make <file.ail> - Process a .ail file (convert, build, debug)")
                 print(f"interactive     - Start interactive session (template or .ail)")
                 print(f"clean           - Remove generated project directories")
                 print(colored("Configuration:", COLOR_PROMPT))
                 print(f"provider <hf|or|google|requesty> - Set AI provider")
                 print(f"config <provider> <key>           - Set API key for the provider")
                 print(f"model                             - Change the model for the current provider")
                 print(f"status                            - Show current configuration status")
                 print(colored("Other:", COLOR_PROMPT))
                 print(f"help            - Show this help message")
                 print(f"exit            - Quit the application")
                 print(colored("Interactive Mode Commands (use 'help' inside interactive mode):", COLOR_PROMPT))
                 print("show, modify, explain, ev, optimize, add, build, run, done")


            elif base_cmd == 'make':
                file_path = args
                if not file_path:
                     print_error("Usage: make <file.ail>")
                     continue
                file_path = file_path.strip('\'"')
                abs_file_path = os.path.abspath(file_path)
                if not os.path.exists(abs_file_path):
                     print_error(f"Input file not found: {abs_file_path}")
                     continue
                if not abs_file_path.endswith('.ail'):
                     print_error("Input file must be a .ail file")
                     continue
                interpreter.process_file(abs_file_path)

            elif base_cmd == 'interactive':
                source_arg = args.strip('\'"')
                if source_arg and source_arg.endswith('.ail'):
                    abs_ail_file = os.path.abspath(source_arg)
                    if os.path.exists(abs_ail_file):
                        interpreter.interactive_session(abs_ail_file)
                    else:
                        print_error(f".ail file not found: {abs_ail_file}")
                elif source_arg:
                     print_error(f"Invalid argument for interactive: '{source_arg}'. Provide a .ail file or no argument to choose a template.")
                else:
                    print_header("Interactive Session Setup")
                    print("Choose source:")
                    print("1. Use a project template")
                    print("2. Use an existing .ail file")
                    while True:
                        choice = prompt_user("Enter choice (1 or 2)")
                        if choice == '1':
                            print_header("Available Project Templates")
                            for key, template_info in PROJECT_TEMPLATES.items():
                                print(f"{key}. {template_info['name']}")
                            while True:
                                template_choice = prompt_user("Select template number")
                                if template_choice in PROJECT_TEMPLATES:
                                    selected_template = PROJECT_TEMPLATES[template_choice]
                                    print_success(f"Selected template: {selected_template['name']}")
                                    interpreter.interactive_session(selected_template['description'])
                                    break
                                else:
                                    print_error("Invalid template number.")
                            break
                        elif choice == '2':
                            while True:
                                ail_file = prompt_user("Enter the path to the .ail file")
                                if not ail_file:
                                    print_warning("No file specified.")
                                    continue
                                ail_file = ail_file.strip('\'"')
                                abs_ail_file = os.path.abspath(ail_file)
                                if not os.path.exists(abs_ail_file):
                                    print_error(f".ail file not found: {abs_ail_file}")
                                elif not abs_ail_file.endswith('.ail'):
                                    print_error("File must be a .ail file")
                                else:
                                    interpreter.interactive_session(abs_ail_file)
                                    break
                            break
                        else:
                            print_error("Invalid choice. Please enter 1 or 2.")


            elif base_cmd == 'clean':
                interpreter.clean_files()

            elif base_cmd == 'config':
                config_parts = args.split(maxsplit=1)
                provider_key = config_parts[0].lower() if config_parts else ""
                api_key_value = config_parts[1] if len(config_parts) > 1 else ""

                valid_providers = ["hf", "or", "google", "requesty"]
                if provider_key in valid_providers:
                    if not api_key_value:
                        print_error(f"Usage: config {provider_key} <your_api_key>")
                        continue
                    interpreter.api_keys[provider_key] = api_key_value
                    interpreter.config[f"{provider_key}_api_key"] = api_key_value
                    interpreter.save_config()
                    print_success(f"{provider_key.capitalize()} API key updated.")
                    if interpreter.provider == provider_key:
                        interpreter.setup_api_config()
                else:
                     print_error(f"Invalid provider '{provider_key}'. Usage: config <hf|or|google|requesty> <your_api_key>")


            elif base_cmd == 'provider':
                 provider_choice = args.strip().lower()
                 interpreter.change_provider(provider_choice)


            elif base_cmd == 'model':
                interpreter.change_model()

            elif base_cmd == 'status':
                provider_name = "None"
                provider_code = interpreter.provider or 'N/A'
                if interpreter.provider == "hf": provider_name = "HuggingFace"
                elif interpreter.provider == "or": provider_name = "OpenRouter"
                elif interpreter.provider == "google": provider_name = "Google AI"
                elif interpreter.provider == "requesty": provider_name = "Requesty"

                model_name = interpreter.model_info.get(interpreter.provider, "N/A") if interpreter.provider else "N/A"

                def key_status(key_type):
                    return colored('Yes', COLOR_SUCCESS) if interpreter.api_keys.get(key_type) else colored('No', COLOR_ERROR)

                print_header("Current Status")
                print(f"Provider: {colored(provider_name, COLOR_INFO)} ({provider_code})")
                print(f"Model: {colored(model_name, COLOR_INFO)}")
                print(f"HF API Key Set: {key_status('hf')}")
                print(f"OR API Key Set: {key_status('or')}")
                print(f"Google API Key Set: {key_status('google')}")
                print(f"Requesty API Key Set: {key_status('requesty')}")
                print(f"Config File: {CONFIG_FILE}")
                print(f"Tracked Projects: {len(interpreter.config.get('project_dirs', []))}")


            else:
                print_error(f"Unknown command: '{command}'. Type 'help' for available commands.")

        except KeyboardInterrupt:
             print_warning("\nOperation interrupted by user. Exiting.")
             break
        except (ConnectionError, TimeoutError) as e:
             print_error(f"API Error: {e}")
             print_warning("Check API key, provider settings ('status' command), and internet connection.")
        except EOFError:
             print_info("\nEnd of input detected. Exiting.")
             break
        except Exception as e:
             print_error(f"An unexpected error occurred: {e}")
             import traceback
             traceback.print_exc()
             print_warning("If the problem persists, please report the issue or try restarting.")


if __name__ == "__main__":
    main()
