# -*- coding: utf-8 -*-
from django.urls import path, re_path
from rest_framework import permissions
from .views import ImageFileUploadView, ImageFileUploadDetailView, ImageFolderUploadView, ImageFolderUploadDetailView, \
    LayoutModelUploadView, LayoutModelUploadDetailView, OCRModelUploadView, OCRModelUploadDetailView, \
    OCRView, OCRFolderView, IndexPageView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="OCCAM Pero-ocr API",
        default_version='v1',
        description="Documentation for REST API",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="nobody@crosslang.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', IndexPageView.as_view()),
    path('uploads/', ImageFileUploadView.as_view()),
    path('uploads/<int:pk>/', ImageFileUploadDetailView.as_view()),
    path('upload_folders/', ImageFolderUploadView.as_view()),
    path('upload_folders/<int:pk>/', ImageFolderUploadDetailView.as_view()),
    path('layout_models/', LayoutModelUploadView.as_view()),
    path('layout_models/<int:pk>/', LayoutModelUploadDetailView.as_view()),
    path('ocr_models/', OCRModelUploadView.as_view()),
    path('ocr_models/<int:pk>/', OCRModelUploadDetailView.as_view()),
    path('ocr/', OCRView.as_view()),
    path('ocr_folder/', OCRFolderView.as_view()),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc')
]
