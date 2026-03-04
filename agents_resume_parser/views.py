from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .utils import extract_text_from_pdf, extract_text_from_txt
from .agent import parse_resume_text
from resumes.models import Resume

class ParseResumeView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    from rest_framework.permissions import IsAuthenticated
    from accounts.permissions import IsJobSeeker
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('resume')
        
        if not file_obj:
            return Response({"error": "No resume file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        file_name = file_obj.name.lower()
        file_bytes = file_obj.read()
        
        try:
            # Save the parsed_state to DB before returning
            print("[DEBUG - VIEW] Starting file extraction...")
            
            if file_name.endswith('.pdf'):
                text = extract_text_from_pdf(file_bytes)
            elif file_name.endswith('.txt'):
                text = extract_text_from_txt(file_bytes)
            else:
                return Response({"error": "Unsupported file format. Please upload PDF or TXT."}, 
                              status=status.HTTP_400_BAD_REQUEST)
                              
            print(f"[DEBUG - VIEW] Text extracted successfully. Length: {len(text)}")
            
            # Send text to AI
            parsed_data = parse_resume_text(text)
            
            if "error" in parsed_data:
                print(f"[DEBUG - VIEW] Parsing error: {parsed_data['error']}")
                return Response(parsed_data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                
            # Create the model record
            resume_obj = Resume.objects.create(
                user=request.user,
                file=file_obj,
                parsed_data=parsed_data
            )
            
            print(f"[DEBUG - VIEW] Saved Resume ID {resume_obj.id} successfully.")
            return Response({"parsed_state": parsed_data, "resume_id": resume_obj.id}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
