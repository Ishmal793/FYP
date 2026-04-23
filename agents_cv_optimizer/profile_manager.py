import json
import os
from groq import Groq

def run_profile_memory_manager(existing_profile: dict, extracted_data: dict, user_confirmation: bool):
    """
    Decides how extracted resume fields should be saved into a user profile.
    Ensures NO duplicate data is stored and merges intelligently.
    """
    if not user_confirmation:
        return {
            "update_profile": False,
            "message": "No changes were made to the user profile."
        }

    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)

    system_prompt = """
    You are a Career Profile Memory Manager inside an AI Resume Optimization System.
    Your job is to decide how extracted resume fields should be saved into a user profile and ensure NO duplicate data is stored.

    DEDUPLICATION RULES:
    - Skills: Case-insensitive unique list.
    - Experience: Unique by job title + company name.
    - Projects: Unique by project title.
    - Education: Unique by institution + degree.
    - Certifications: Unique by name.

    STRICT RULES:
    - DO NOT create new information.
    - DO NOT hallucinate missing fields.
    - DO NOT duplicate existing entries.
    - Normalize data before saving (e.g. Python == python).

    OUTPUT FORMAT (STRICT JSON ONLY):
    {
      "update_profile": true,
      "merged_profile": {
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": []
      },
      "new_additions": {
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": []
      },
      "message": "Profile updated successfully without duplicates."
    }
    """

    user_prompt = f"""
    Existing Profile:
    {json.dumps(existing_profile)}

    New Extracted CV Data:
    {json.dumps(extracted_data)}

    User Confirmation: YES
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        response_text = chat_completion.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        return {
            "update_profile": False,
            "message": f"Error during profile merging: {str(e)}"
        }
