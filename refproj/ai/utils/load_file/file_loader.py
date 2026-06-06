import os

class TextLoader:

    def load(self, file_path):

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.endswith(".txt"):
            raise ValueError("File must be a .txt file")

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return text