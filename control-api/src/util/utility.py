from email.message import EmailMessage
from datetime import datetime, timedelta
import os
from typing import Dict, Any
from sentence_transformers import SentenceTransformer
from io import BytesIO
from PIL import Image
from pathlib import Path


import smtplib
import base64
import json
import string
import random
import requests
import xlrd
import re
import hashlib
import mimetypes
import regex
import requests 

from openai import OpenAI





class Util():


    def check_image_exists(image_url):        
        try:
            response = requests.get(image_url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            # Handle any exception (timeout, connection error, etc.)
            return False
    
    def get_extension_pathlib(filename):
        return Path(filename).suffix  # Returns extension with the dot
        
    def get_extension_pathlib_without_dot(filename):
        return Path(filename).suffix[1:]  # Returns extension without the dot

    def get_tokens_no(text):
        """
        Basic token counter for Python 1.3
        Splits text by whitespace and punctuation
        """
        # Replace common punctuation with spaces
        for char in ',.!?;:()[]{}"\'`':
            text = string.replace(text, char, ' ')
        
        # Split by whitespace
        tokens = string.split(text)
        
        # Filter out empty tokens
        tokens = filter(lambda x: x, tokens)
        
        return len(tokens)

    def get_tokens_no_regex(self, text):
        """
        More sophisticated token counter using regex
        Identifies words, numbers, and punctuation as separate tokens
        """
        # Pattern for words, numbers, and punctuation
        pattern = regex.compile(r'[A-Za-z]+|[0-9]+|[,.!?;:()\[\]{}]')
        
        # Find all matches
        matches = pattern.findall(text)
        
        return len(matches)

    def get_tokens_no_from_file(self,filename):
        """
        Count tokens in a file
        """
        try:
            f = open(filename, 'r')
            content = f.read()
            f.close()
            return self.get_tokens_no_regex(content)
        except IOError:
            print ("Error: Could not open file", filename)
            return 0

    
    def load_prompt_from_json(self, prompts_directory: str, prompt_name: str) -> Dict[str, Any]:
        """Load a prompt configuration from a JSON file."""
        file_path = os.path.join(prompts_directory, f"{prompt_name}.json")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                prompt_config = json.load(file)
                # self.loaded_prompts[prompt_name] = prompt_config
                return prompt_config
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in prompt file: {file_path}")    
    
    
    

   


    def get_chunk_text(content,chunk_size=512,overlap_size=100):
        """
        Split the content into overlapping chunks.
        
        Args:
            content (str): The input text to be chunked
            
        Returns:
            list: A list of text chunks with specified overlap
        """
        # Check if content is empty or None
        # chunk_size=512
        # overlap_size=100
        if not content:
            return []
            
        # Initialize variables
        chunks = []
        start_idx = 0
        
        # Continue chunking until we've processed the entire text
        while start_idx < len(content):
            # Calculate end index for current chunk
            end_idx = min(start_idx + chunk_size, len(content))
            
            # If we're not at the end of the text, try to find a good breakpoint
            if end_idx < len(content):
                # Look for sentence boundary (period followed by space)
                # Look backwards from the end of the potential chunk
                breakpoint_candidates = [
                    content.rfind(". ", start_idx, end_idx),
                    content.rfind("? ", start_idx, end_idx),
                    content.rfind("! ", start_idx, end_idx),
                    content.rfind("\n", start_idx, end_idx)
                ]
                
                # Find the best breakpoint (take the furthest one that exists)
                breakpoint = max(breakpoint_candidates)
                
                # If found a good breakpoint, adjust end_idx to include the punctuation and space
                if breakpoint != -1:
                    end_idx = breakpoint + 2  # Include the punctuation and space
            
            # Extract the chunk
            chunk = content[start_idx:end_idx].strip()
            
            # Only add non-empty chunks
            if chunk:
                chunks.append(chunk)
            
            # Move start index for next chunk, taking overlap into account
            start_idx = end_idx - overlap_size
            
            # Ensure we're making progress
            if start_idx >= end_idx:
                start_idx = end_idx
        
        return chunks

    def get_embeding(contents,models='BAAI/bge-m3'):
        model = SentenceTransformer(models)
        embeddings = model.encode(contents).tolist()
        del model
        return embeddings
    
    def get_api_key(self):
        file = open('././config/config.json')
        data = json.load(file)
        api_key=data["openai-key"]
        return api_key
    

    def get_key_value(self,key):
        file = open('././config/config.json')
        data = json.load(file)
        key_value=data[key]
        return key_value
    

    def get_models_list(self):
        api_key=self.get_key_value("openai-key")
        client = OpenAI(
            # Set your API key here, or preferably use environment variables
            api_key=api_key
        )
        raw_data=models = client.models.list()
        raw_data = str(raw_data)
        model_pattern = r"Model\(id='([^']+)', created=(\d+), object='([^']+)', owned_by='([^']+)'\)"
        matches = re.findall(model_pattern, raw_data)
        model_ids = [match[0] for match in matches]
        return model_ids
    
    
    def get_models_list_by_key(self,api_key):
        client = OpenAI(
            api_key=api_key
        )
        raw_data=models = client.models.list()
        raw_data = str(raw_data)
        model_pattern = r"Model\(id='([^']+)', created=(\d+), object='([^']+)', owned_by='([^']+)'\)"
        matches = re.findall(model_pattern, raw_data)
        model_ids = [match[0] for match in matches]
        return model_ids

   
    
    def clean_string(text):
        """
        Remove excessive whitespace and normalize newlines in a string.
        """
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n{2,}', '\n', text)
        
        # Alternative without regex (slightly less efficient but more readable)
        # while '\n\n' in text:
        #     text = text.replace('\n\n', '\n')
        
        return text

    
    def get_chunks_text(text, chunk_size=512, chunk_overlap=100):
   
        chunks = []
        start = 0



        chunk_size=int(chunk_size)
        chunk_overlap=int(chunk_overlap)
        #print(type(chunk_size))
        
        if(len(text)>chunk_size):
            while start < len(text):
                # Calculate end position with chunk_size
                end = min(start + chunk_size, len(text))
                
                # If not at the end of text, try to find a good break point
                if end < len(text):
                    # Look for nearest space, newline or punctuation
                    for i in range(end, max(start, end - 50), -1):
                        if text[i] in " \n.,;!?":
                            end = i + 1  # Include the delimiter
                            break
                
                # Add chunk to our list
                chunks.append(text[start:end])
                
                # Move start position considering overlap
                start = end - chunk_overlap
        else:
            chunks=text 
        
        return chunks

 

    

    def check_filetype_basic(file_contents, filename=None):
            # Try to detect common image formats
        
            img_type = Image.open(BytesIO(file_contents)).format.lower() if file_contents else None
            if img_type:
                return f"image/{img_type}"
            
            # Fall back to extension-based detection if filename is provided
            if filename:
                return mimetypes.guess_type(filename)[0] or "application/octet-stream"
    
            return "application/octet-stream"  # Default binary type
    
    

    def hash_password(password):
        # Encode the password to bytes and generate MD5 hash
        return hashlib.md5(password.encode()).hexdigest()

    def dict_keys_to_string(to_dict_method):
        # Extract field names from the to_dict method
        lines = to_dict_method.strip().split('\n')
        field_names = []

        for line in lines:
            # Look for lines with the pattern 'field_name': self.field_name
            if "'" in line and ":" in line and "self." in line:
                # Extract field name between quotes
                field_name = line.split("'")[1].strip()
                field_names.append(field_name)

        # Convert the list to a string representation
        field_names_string = str(field_names)
        return field_names_string

    def string_to_tuple(input_string: str,) -> tuple:
        # Split the string by spaces
        words = input_string.split()
        # Convert the list of words to a tuple
        result_tuple = tuple(words)
        return result_tuple

    def string_to_array(input_string):
        # Split the string by spaces
        words = input_string.split()

        # Return the list of words
        return words

    def get_field_names(to_dict_method_string):
        # Find all lines with pattern: 'field_name': self.field_name,
        field_lines = [line.strip() for line in to_dict_method_string.split('\n')
                       if ':' in line and 'self.' in line]

        # Extract just the field names from these lines
        field_names = []
        for line in field_lines:
            # Get the part before the colon and remove quotes and spaces
            field_name = line.split(':')[0].strip().strip("'\"")
            field_names.append(field_name)

        return field_names


    def get_text_date_bds(date_str):
        """Convert a date string from 'Y-m-d' to 'dd-mm-yyyy' format with year adjusted by +543."""
        def get_format(value):
            """Format the value to ensure two digits."""
            return f"{value:02d}"
        try:
            # Parse the date string
            #print(str(date_str)[:10])
            date_obj = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            # return None
            # Extract day, month, and year
            day = get_format(date_obj.day)
            month = get_format(date_obj.month)
            year = date_obj.year + 543  # Adjust the year
            #
            # # Return formatted date string
            return f"{day}-{month}-{year}"

        except ValueError as e:
            # Handle the case where the date string is not in the expected format
            print(f"Error parsing date: {e}")
            return None  # Or you can return a default value or raise an

    def get_receivers():
        # Open the JSON configuration file
        with open('././config/config.json', 'r') as file:
            # Load the JSON data
            data = json.load(file)

        # Access the email_receivers element
        email_receivers = data.get("receivers")

        # Check if email_receivers exists and convert to a list if needed
        if email_receivers:
            # If email_receivers is a string, convert it to a list
            if isinstance(email_receivers, str):
                email_receivers = [email_receivers]
        else:
            email_receivers = []
        return email_receivers

    def send_email(email_receivers,subject,detail):
            with open('././config/config.json', 'r') as file:
                data = json.load(file)
            # Access the mail_senders element
            mail_senders = data.get("mail_senders")
            #print(mail_senders)
            email_sender=""
            password=""

            if mail_senders:
                email_sender = mail_senders.get("sender")
                password = mail_senders.get("password")
            else:
                print("No mail_senders found in the configuration.")
                return None


            subject = subject
            body = detail

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = email_sender
            msg['To'] = ', '.join(email_receivers)  # Join the list into a comma-

            msg.set_content(body)

            try:
                with smtplib.SMTP('smtp.office365.com', 587) as smtp:
                    smtp.starttls()  # Start TLS encryption
                    smtp.login(email_sender, password)  # Log in to the email account
                    smtp.send_message(msg)  # Send the email
                    print("Email sent successfully!")
                    return {"Flag":True,"Message":"Email sent successfully!"}
            except Exception as e:
                    print("Failed to send email!")
                    return {"Flag":False,"Message":f"Failed to send email: {e}"}

    def is_excel_97_2003(file_path):
        try:
            # Attempt to open the file with xlrd
            workbook = xlrd.open_workbook(file_path)
            return True  # If successful, it's an .xls file
        except xlrd.XLRDError:
            return False  # If an error occurs, it's not an .xls file

    def extract_and_pop(original_string, substring):
        if substring in original_string:
            # Find the index of the substring
            index = original_string.find(substring)
            # Extract the substring
            extracted_substring = original_string[index:index + len(substring)]
            # Remove the substring from the original string
            modified_string = original_string[:index] + original_string[index + len(substring):]

            return extracted_substring, modified_string
        else:
            return None, original_string

    def get_last_element(original_str,saparate):
        results = original_str.split('.')
        l=len(results)-1
        result =    results[l] if l>0 else None
        return result

    def get_url():
        file = open('././config/config.json')
        data = json.load(file)
        url=data["front_end_url"]
        return url


    def send_line_notify(message):

        file = open('././config/config.json')
        data = json.load(file)
        token=data["line_token"]
        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Authorization': 'Bearer ' + token,
        }
        payload = {
            'message': message,
        }
        r = requests.post(url, headers=headers, params=payload)
        return r.status_code




    def dict_to_statment(fields:dict):
        stms=""
        field_count=field_count(fields)
        i=0
        for value in fields.items():
            if(i<field_count-1):
                stms+=value+","
            else:
                stms+=value
            i+=1
        return stms

    def generate_password(length):
        characters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(random.choice(characters) for _ in range(length))
        return password

    def encode(original_string:str):
        encoded_bytes = base64.b64encode(original_string.encode('utf-8'))
        encoded_string = encoded_bytes.decode('utf-8')
        return encoded_string

    def decode(encoded_string):
        encoded_bytes = base64.b64decode(encoded_string)
        decoded_string = encoded_bytes.decode('utf-8')
        return decoded_string



    def is_number_tryexcept(number_val:str):
        """ Returns True if string is a number. """
        try:
            float(number_val)
            return True
        except ValueError:
            return False


    def is_number_regex(number_val: str):
        """ Returns True if string is a number (integer or float). """
        # Check if it's a floating point number
        if re.match(r"^[-+]?\d*\.?\d+$", number_val) is not None:
            return True
        # Check if it's an integer or scientific notation
        return re.match(r"^[-+]?\d+$|^[-+]?\d*\.?\d+[eE][-+]?\d+$", number_val) is not None

    def increment_time(start_time, increment_minutes=30):
        # Parse the time string
        time_obj = datetime.strptime(start_time, '%H:%M')

        # Add increment
        new_time = time_obj + timedelta(minutes=increment_minutes)

        # Format back to string
        return new_time.strftime('%H:%M')

    def is_code_blocks_found(text):
        pattern = r"```(.*?)```"
        code_blocks = re.findall(pattern, text, re.DOTALL)

        # Check if code_blocks has elements
        if code_blocks:
            print("Code blocks found:")
            for i, block in enumerate(code_blocks, start=1):
                print(f"Block {i}:")
                print(block)
        else:
            print("No code blocks found.")

        return bool(code_blocks)
    
    def find_triple_dat_tokens(text:str):
        """
        Find all occurrences of triple backticks (```).
        
        Parameters:
            text (str): The input string to search for triple backticks.
            
        Returns:
            list: A list of indices where triple backticks are found.
        """
        # Regex pattern to match triple backticks
        pattern = r"---"
        
        # Find all matches
        matches = [match.start() for match in re.finditer(pattern, text)]


        return bool(matches)
        
    

    def find_triple_backtick_tokens(text:str):
        """
        Find all occurrences of triple backticks (```).
        
        Parameters:
            text (str): The input string to search for triple backticks.
            
        Returns:
            list: A list of indices where triple backticks are found.
        """
        # Regex pattern to match triple backticks
        pattern = r"```"
        
        # Find all matches
        matches = [match.start() for match in re.finditer(pattern, text)]


        return bool(matches)
    
   
    def detect_latex(text):
        patterns = [
                r"\$\$.*?\$\$",         # $$...$$
                r"\\\[.*?\\\]",         # \[...\]
                r"\\\(.*?\\\)",         # \(...\)
                r"\\[a-zA-Z]+",         # \command
                r"\\begin\{.*?\}",      # \begin{...}
                r"\\end\{.*?\}",        # \end{...}
        ]
    
        matches = []
        for pattern in patterns:
            matches.extend(re.findall(pattern, text))

        return {"is_latex": len(matches) > 0, "matches": matches}
    


    def extract_specific_elements(text, positions=None):
        """
        Extract specific elements from comma-separated values in code blocks.
        
        Args:
            text (str): Text containing code blocks with CSV data
            positions (list): List of indices to extract (0-based). If None, extract all.
            
        Returns:
            list: List of extracted elements
        """
        # Find code blocks
        pattern = r"```(.*?)```"
        code_blocks = re.findall(pattern, text, re.DOTALL)
        
        extracted_elements = []
        for block in code_blocks:
            # Process each line
            lines = block.strip().split('\n')
            for line in lines:
                if ',' in line:
                    elements = line.split(',')
                    
                    # Extract all elements or specific positions
                    if positions is None:
                        extracted_elements.extend(elements)
                    else:
                        for pos in positions:
                            if 0 <= pos < len(elements):
                                extracted_elements.append(elements[pos])
        
        return extracted_elements
    
    def format_as_markdown(data, metadata):
        """Format the extracted data as Markdown with metadata."""
        output = []
        output.append("# Extracted Data Report")
        output.append(f"**Timestamp:** {metadata['timestamp']}  ")
        output.append(f"**User:** {metadata['user']}  ")
        output.append(f"**Created:** {metadata['created_at']}  ")
        output.append(f"**Number of extractions:** {metadata['extraction_count']}  ")
        output.append("\n")
        
        for i, block in enumerate(data):
            output.append(f"## Block {i+1}")
            output.append("```")
            for row in block:
                if isinstance(row, list):
                    output.append(",".join(row))
                else:
                    output.append(str(row))
            output.append("```")
            output.append("\n")
        
        return "\n".join(output)

    def format_as_html(data):
        """Format the extracted data as HTML with metadata."""
        output = []
        output.append("<!DOCTYPE html>")
        output.append("<html>")
        output.append("<head>")
        output.append("  <title>Extracted Data Report</title>")
        output.append("  <style>")
        output.append("    body { font-family: Arial, sans-serif; margin: 20px; }")
        output.append("    .metadata { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }")
        output.append("    .block { margin: 20px 0; }")
        output.append("    .block-title { font-weight: bold; }")
        output.append("    table { border-collapse: collapse; width: 100%; }")
        output.append("    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        output.append("    th { background-color: #f2f2f2; }")
        output.append("  </style>")
        output.append("</head>")
        output.append("<body>")
        output.append("  <h1>Extracted Data Report</h1>")
        # output.append("  <div class='metadata'>")
        # output.append(f"    <p><strong>Timestamp:</strong> {metadata['timestamp']}</p>")
        # output.append(f"    <p><strong>User:</strong> {metadata['user']}</p>")
        # output.append(f"    <p><strong>Created:</strong> {metadata['created_at']}</p>")
        # output.append(f"    <p><strong>Number of extractions:</strong> {metadata['extraction_count']}</p>")
        # output.append("  </div>")
        
        for i, block in enumerate(data):
            output.append(f"  <div class='block'>")
            output.append(f"    <h2 class='block-title'>Block {i+1}</h2>")
            output.append("    <table>")
            
            for j, row in enumerate(block):
                output.append("      <tr>")
                if isinstance(row, list):
                    for cell in row:
                        tag = "th" if j == 0 else "td"
                        output.append(f"        <{tag}>{cell}</{tag}>")
                else:
                    output.append(f"        <td>{row}</td>")
                output.append("      </tr>")
            
            output.append("    </table>")
            output.append("  </div>")
        
        output.append("</body>")
        output.append("</html>")
        
        return "\n".join(output)
