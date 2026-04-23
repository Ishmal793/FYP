from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from resumes.models import Resume
from .rag_service import generate_grounded_response

class CareerCoachChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_query = request.data.get("query")
        resume_id = request.data.get("resume_id")
        
        if not user_query:
            return Response({"error": "Query is required."}, status=400)

        # Retrieve Context (RAG)
        context = {}
        if resume_id:
            try:
                resume = Resume.objects.get(id=resume_id, user=request.user)
                context["resume"] = resume.parsed_data
                context["skill_gap"] = resume.skill_gap_data
                context["target_role"] = resume.locked_target_role
            except Resume.DoesNotExist:
                pass
        
        # If no resume, use general profile context
        if not context:
            # Add general profile context if needed
            pass

        answer = generate_grounded_response(user_query, context)
        
        return Response({
            "success": True,
            "answer": answer
        })
