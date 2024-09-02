import tiktoken
import os

def estimate_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Estimate the number of tokens in a given text."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))

def estimate_file_tokens(file_path: str, encoding_name: str = "cl100k_base") -> int:
    """Estimate the number of tokens in a file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return estimate_tokens(content, encoding_name)

def estimate_project_tokens(project_root: str, file_extensions: list[str], encoding_name: str = "cl100k_base") -> dict:
    """Estimate tokens for all files with specified extensions in a project."""
    total_tokens = 0
    file_token_counts = {}

    for root, _, files in os.walk(project_root):
        for file in files:
            if any(file.endswith(ext) for ext in file_extensions):
                file_path = os.path.join(root, file)
                tokens = estimate_file_tokens(file_path, encoding_name)
                file_token_counts[file_path] = tokens
                total_tokens += tokens

    return {
        "total_tokens": total_tokens,
        "file_token_counts": file_token_counts
    }

def estimate_cost(total_tokens: int, price_per_1k_tokens: float) -> float:
    """Estimate the cost based on total tokens and price per 1000 tokens."""
    return (total_tokens / 1000) * price_per_1k_tokens

# Example usage
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tell me about")
    parser.add_argument("project_root", type=str, help="Path to the project root")
    args = parser.parse_args()

    project_root = args.project_root

    file_extensions = [".java", ".xml", ".properties", ".yaml", ".yml"]
    # Anthropomorphic Claude Sonnet 3.5 $3 per million tokens
    price_per_1k_tokens = 0.003  # Adjust this based on your LLM's pricing

    print(f"Estimating tokens for project at: {project_root} with file extensions: {file_extensions} ...")
    print(f"price for 1k tokens: ${price_per_1k_tokens:.3f}")

    estimation = estimate_project_tokens(project_root, file_extensions)
    total_tokens = estimation["total_tokens"]
    file_token_counts = estimation["file_token_counts"]

    print(f"Total estimated tokens: {total_tokens}")
    print(f"Estimated cost: ${estimate_cost(total_tokens, price_per_1k_tokens):.2f}")

    print("\nToken counts by file:")
    for file, count in file_token_counts.items():
        print(f"{file}: {count} tokens")
