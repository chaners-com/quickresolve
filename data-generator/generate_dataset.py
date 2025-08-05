import os
import time
from pathlib import Path

import google.generativeai as genai

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


def generate_customer_service_ticket(ticket_number):
    """Generate a single customer service ticket using Gemini API."""

    prompt = f"""
    Create a realistic customer service ticket #{ticket_number:03d} in \
    Markdown format.
    This should be a fake but believable customer service issue and resolution.

    The file should include:
    - A clear title describing the issue
    - Customer's reported problem (realistic details)
    - Step-by-step resolution process
    - Final outcome
    - Relevant keywords/tags

    Make it sound like a real customer service ticket from a tech company.
    Include specific details like email addresses, error messages, product \
names, etc.
    Keep it between 20-50 lines.

    Format it as a clean Markdown file with headers and bullet points.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating ticket {ticket_number}: {e}")
        return None


def main():
    """Generate 100 customer service tickets."""

    # Create output directory
    output_dir = Path("customer_service_data")
    output_dir.mkdir(exist_ok=True)

    print("Starting dataset generation...")
    print(f"Output directory: {output_dir.absolute()}")

    successful_generations = 0

    for i in range(1, 101):  # Generate 100 files
        print(f"Generating ticket {i}/100...")

        content = generate_customer_service_ticket(i)

        if content:
            # Create filename
            filename = f"ticket_{i:03d}.md"
            filepath = output_dir / filename

            # Write content to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            successful_generations += 1
            print(f"✓ Created {filename}")
        else:
            print(f"✗ Failed to generate ticket {i}")

        # Add a small delay to be respectful to the API
        time.sleep(1)

    print("\nDataset generation complete!")
    print(f"Successfully generated {successful_generations}/100 files")
    print(f"Files saved in: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
