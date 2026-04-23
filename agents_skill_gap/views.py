from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from resumes.models import Resume
from jobs.models import JobResult
from .models import SkillGapReport, CourseRecommendation
from .agent import generate_learning_roadmap

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_roadmap(request):
    resume_id = request.data.get('resume_id')
    job_details = request.data.get('job_details')
    
    if not resume_id or not job_details:
        return Response({'error': 'resume_id and job_details are required'}, status=400)
        
    try:
        resume = Resume.objects.get(id=resume_id, user=request.user)
    except Exception:
        return Response({'error': 'Resume not found or access denied'}, status=404)
        
    parsed_data = resume.parsed_data
    
    target_job_info = {
        'title': job_details.get('title'),
        'description': job_details.get('description'),
        'missing_keywords': job_details.get('missing_keywords', [])
    }
    
    roadmap_data = generate_learning_roadmap(parsed_data, target_job_info)
    
    report = SkillGapReport.objects.create(
        user=request.user,
        resume=resume,
        target_job=None,
        target_role_title=job_details.get('title', 'Unknown Title'),
        missing_skills=roadmap_data.get('missing_skills_identified', [])
    )
    
    for course in roadmap_data.get('courses', []):
        CourseRecommendation.objects.create(
            report=report,
            skill=course.get('skill', ''),
            course_title=course.get('course_title', ''),
            platform=course.get('platform', ''),
            duration_estimate=course.get('duration_estimate', '')
        )
        
    return Response({
        'report_id': report.id,
        'roadmap': roadmap_data
    })
