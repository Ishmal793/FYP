from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .utils import extract_text_from_pdf, extract_text_from_txt
from .agent import parse_resume_text
from .nlp_utils import extract_skills_nlp
from resumes.models import Resume
from career_platform.orchestrator import WorkflowOrchestrator

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
            
            # --- PHASE 3: SpaCy Dictionary NLP Integration ---
            try:
                print("[DEBUG - VIEW] Running SpaCy Dictionary extraction...")
                spacy_skills = extract_skills_nlp(text)
                print(f"[DEBUG - VIEW] SpaCy Dictionary Extracted: {len(spacy_skills)} skills")
                
                # Merge AI Skills (List of dicts) + Dictionary Skills (List of strings)
                current_skills_list = parsed_data.get('skills', [])
                current_skill_names = { (s.get('name', '').lower() if isinstance(s, dict) else str(s).lower()) : s for s in current_skills_list }
                
                for s in spacy_skills:
                    if s.lower() not in current_skill_names:
                        current_skill_names[s.lower()] = {"name": s, "level": "Beginner", "reason": "Dictionary Match"}
                
                parsed_data['skills'] = list(current_skill_names.values())
            except Exception as e:
                print(f"[DEBUG - VIEW] Warning: SpaCy Extraction failed: {str(e)}")
            # --------------------------------------------------

            # Create the model record
            resume_obj = Resume.objects.create(
                user=request.user,
                file=file_obj,
                parsed_data=parsed_data
            )
            
            # Orchestrator Trigger: Init or Hash Track
            WorkflowOrchestrator.process_resume_update(resume_obj.id)
            
            print(f"[DEBUG - VIEW] Saved Resume ID {resume_obj.id} successfully.")
            return Response({"parsed_state": parsed_data, "resume_id": resume_obj.id}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateParsedResumeView(APIView):
    from rest_framework.permissions import IsAuthenticated
    from accounts.permissions import IsJobSeeker
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def put(self, request, resume_id, *args, **kwargs):
        try:
            resume = Resume.objects.get(id=resume_id, user=request.user)
            parsed_data = request.data.get('parsed_data')
            if not parsed_data:
                return Response({"error": "No parsed data provided."}, status=status.HTTP_400_BAD_REQUEST)
                
            resume.parsed_data = parsed_data
            resume.save()
            
            # Orchestrator Trigger: Forces Pipeline flush if hash is dirty
            WorkflowOrchestrator.process_resume_update(resume.id)
            
            # Reload to return the Normalizer's safe output (if edited)
            resume.refresh_from_db()
            
            return Response({"message": "Successfully updated parsed data.", "pipeline_status": resume.pipeline_status}, status=status.HTTP_200_OK)
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)

class CompletedResumesListView(APIView):
    from rest_framework.permissions import IsAuthenticated
    from accounts.permissions import IsJobSeeker
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def get(self, request, *args, **kwargs):
        resumes = Resume.objects.filter(user=request.user, ats_completed=True).order_by('-created_at')
        data = []
        for r in resumes:
            data.append({
                "id": r.id,
                "role": r.locked_target_role or "Unknown Role",
                "score": r.ats_score_overall or 0,
                "created_at": r.created_at,
                "file_url": r.file.url if r.file else None,
                "filename": r.file.name.split('/')[-1] if r.file else "Resume.pdf"
            })
        return Response({"resumes": data}, status=status.HTTP_200_OK)

class MarkAtsCompletedView(APIView):
    from rest_framework.permissions import IsAuthenticated
    from accounts.permissions import IsJobSeeker
    permission_classes = [IsAuthenticated, IsJobSeeker]
    
    def post(self, request, *args, **kwargs):
        resume_id = request.data.get('resume_id')
        score = request.data.get('score')
        gap_data = request.data.get('gap_data', {})
        variants = request.data.get('variants', {})
        
        if not resume_id:
            return Response({"error": "resume_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            resume = Resume.objects.get(id=resume_id, user=request.user)
            resume.ats_completed = True
            if score is not None:
                resume.ats_score_overall = score
            if gap_data:
                resume.skill_gap_data = gap_data
            if variants:
                resume.cv_variants = variants
            resume.save()
            return Response({"message": "ATS marked as complete."}, status=status.HTTP_200_OK)
        except Resume.DoesNotExist:
            return Response({"error": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)

