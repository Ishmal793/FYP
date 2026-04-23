from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from resumes.models import Resume
from .agent import predict_career_trajectory

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_trajectory(request):
    resume_id = request.data.get('resume_id')
    
    if not resume_id:
        return Response({'error': 'resume_id is required'}, status=400)
        
    try:
        resume = Resume.objects.get(id=resume_id, user=request.user)
    except Exception:
        return Response({'error': 'Resume not found or access denied'}, status=404)
        
    parsed_data = resume.parsed_data
    trajectory_data = predict_career_trajectory(parsed_data)
    
    return Response({
        'trajectory': trajectory_data
    })
