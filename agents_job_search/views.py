from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsJobSeeker
from .agent import fetch_jobs_from_serpapi

class JobSearchView(APIView):
    permission_classes = [IsAuthenticated, IsJobSeeker]

    def post(self, request, *args, **kwargs):
        titles = request.data.get('titles', [])
        location = request.data.get('location', 'Remote')
        
        if not titles or not isinstance(titles, list):
            return Response({"error": "A list of predicted 'titles' is required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            live_jobs = fetch_jobs_from_serpapi(titles, location)
            return Response({"live_jobs": live_jobs}, status=status.HTTP_200_OK)
            
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
