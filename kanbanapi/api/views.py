"""API Views for KanbanAPI.

Clean endpoints returning flat JSON consistently:
{"success": true, "data": ...} or {"success": false, "error": "..."}
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Article, Tags

import secrets
import string


def ok(data, code=status.HTTP_200_OK):
    return Response({"success": True, "data": data}, status=code)


def err(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"success": False, "error": message}, status=code)


class ArticlesView(APIView):
    """Resource-stable /api/articles/ endpoint.
    GET: list all articles
    POST: create or update article (action in body)
    DELETE: delete article (art_no in body)
    """

    @extend_schema(
        summary="Liste aller Artikel",
        responses={
            200: {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": True},
                                "data": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "art_no": {"type": "string"},
                                            "art_supplier": {
                                                "type": "string",
                                                "enum": ["OKB", "RKB", "SW"],
                                            },
                                            "description": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        }
                    }
                },
            }
        },
        tags=["Articles"],
    )
    def get(self, request):
        qs = Article.objects.all().only("art_no", "art_supplier", "description")
        data = [
            {
                "art_no": a.art_no,
                "art_supplier": a.art_supplier,
                "description": a.description,
            }
            for a in qs
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Artikel art_supplier aktualisieren",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["update"]},
                    "data": {
                        "type": "object",
                        "properties": {
                            "art_no": {"type": "string"},
                            "art_supplier": {
                                "type": "string",
                                "enum": ["OKB", "RKB", "SW"],
                            },
                        },
                        "required": ["art_no", "art_supplier"],
                    },
                },
                "required": ["action", "data"],
            }
        },
        responses={
            200: {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": True},
                                "message": {"type": "string"},
                                "data": {
                                    "type": "object",
                                    "properties": {
                                        "art_no": {"type": "string"},
                                        "art_supplier": {"type": "string"},
                                        "description": {"type": "string"},
                                    },
                                },
                            },
                        }
                    }
                },
            },
            400: {
                "description": "Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string"},
                            },
                        }
                    }
                },
            },
            404: {
                "description": "Article not found",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string"},
                            },
                        }
                    }
                },
            },
        },
        tags=["Articles"],
    )
    def post(self, request):
        body = request.data or {}
        action = body.get("action")
        data = body.get("data", {})

        if action != "update":
            return Response(
                {"success": False, "error": "Only 'update' action is allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        art_no = data.get("art_no")
        art_supplier = data.get("art_supplier")

        if not art_no or not art_supplier:
            return Response(
                {"success": False, "error": "art_no and art_supplier are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if art_supplier not in ["OKB", "RKB", "SW"]:
            return Response(
                {"success": False, "error": "Invalid art_supplier"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        article = Article.objects.filter(art_no=art_no).first()
        if not article:
            return Response(
                {"success": False, "error": "Article not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        article.art_supplier = art_supplier
        article.save()
        return Response(
            {
                "success": True,
                "message": "Article supplier updated",
                "data": {
                    "art_no": article.art_no,
                    "art_supplier": article.art_supplier,
                    "description": article.description,
                },
            },
            status=status.HTTP_200_OK,
        )


def generate_unique_tag_id():
    alphabet = string.hexdigits.upper()
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(24))
        if not Tags.objects.filter(tag_id=candidate).exists():
            return candidate


class TagsView(APIView):
    """Resource-stable /api/tags/ endpoint.
    GET: list all tags
    POST: create, update, set_status, or generate (action in body)
    DELETE: delete tag (tag_id in body)
    """

    @extend_schema(
        summary="Liste aller Tags",
        responses={
            200: {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": True},
                                "data": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "tag_id": {"type": "string"},
                                            "art_no": {"type": "string"},
                                            "status": {"type": "integer"},
                                        },
                                    },
                                },
                            },
                        }
                    }
                },
            }
        },
        tags=["Tags"],
    )
    def get(self, request):
        qs = Tags.objects.select_related("art_no").only(
            "tag_id", "art_no__art_no", "status"
        )
        data = [
            {"tag_id": t.tag_id, "art_no": t.art_no.art_no, "status": t.status}
            for t in qs
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Tag anlegen, aktualisieren, Status setzen oder generieren",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "set_status", "generate"],
                    },
                    "data": {
                        "type": "object",
                        "properties": {
                            "tag_id": {"type": "string"},
                            "art_no": {"type": "string"},
                            "status": {"type": "integer", "enum": [0, 1]},
                            "preferred_tag_id": {"type": "string"},
                        },
                    },
                },
                "required": ["action"],
            }
        },
        responses={
            200: {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": True},
                                "message": {"type": "string"},
                                "data": {
                                    "type": "object",
                                    "properties": {
                                        "tag_id": {"type": "string"},
                                        "art_no": {"type": "string"},
                                        "status": {"type": "integer"},
                                    },
                                },
                            },
                        }
                    }
                },
            },
            400: {
                "description": "Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string"},
                            },
                        }
                    }
                },
            },
        },
        tags=["Tags"],
    )
    def post(self, request):
        body = request.data or {}
        action = body.get("action")
        data = body.get("data", {})

        if not action or action not in ["create", "update", "set_status", "generate"]:
            return Response(
                {"success": False, "error": "Invalid action"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate unique tag_id
        if action == "generate":
            preferred = data.get("preferred_tag_id")
            if preferred and not Tags.objects.filter(tag_id=preferred).exists():
                tag_id = preferred
            else:
                tag_id = generate_unique_tag_id()
            return Response(
                {
                    "success": True,
                    "message": "Tag generated",
                    "data": {"tag_id": tag_id},
                },
                status=status.HTTP_200_OK,
            )

        tag_id = data.get("tag_id")
        art_no = data.get("art_no")
        tag_status = data.get("status", 0)

        if action == "create":
            if not tag_id or not art_no:
                return Response(
                    {"success": False, "error": "tag_id and art_no are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Tags.objects.filter(tag_id=tag_id).exists():
                return Response(
                    {"success": False, "error": "Tag already exists"},
                    status=status.HTTP_409_CONFLICT,
                )
            article = Article.objects.filter(art_no=art_no).first()
            if not article:
                return Response(
                    {"success": False, "error": "Article not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            tag = Tags.objects.create(tag_id=tag_id, art_no=article, status=tag_status)
            return Response(
                {
                    "success": True,
                    "message": "Tag created",
                    "data": {
                        "tag_id": tag.tag_id,
                        "art_no": article.art_no,
                        "status": tag.status,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        elif action == "update":
            if not tag_id:
                return Response(
                    {"success": False, "error": "tag_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tag = Tags.objects.filter(tag_id=tag_id).first()
            if not tag:
                return Response(
                    {"success": False, "error": "Tag not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if art_no:
                article = Article.objects.filter(art_no=art_no).first()
                if not article:
                    return Response(
                        {"success": False, "error": "Article not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                tag.art_no = article
            if "status" in data:
                if tag_status not in [0, 1]:
                    return Response(
                        {"success": False, "error": "status must be 0 or 1"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                tag.status = tag_status
            tag.save()
            return Response(
                {
                    "success": True,
                    "message": "Tag updated",
                    "data": {
                        "tag_id": tag.tag_id,
                        "art_no": tag.art_no.art_no,
                        "status": tag.status,
                    },
                },
                status=status.HTTP_200_OK,
            )

        elif action == "set_status":
            if not tag_id:
                return Response(
                    {"success": False, "error": "tag_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if "status" not in data:
                return Response(
                    {"success": False, "error": "status is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if tag_status not in [0, 1]:
                return Response(
                    {"success": False, "error": "status must be 0 or 1"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tag = Tags.objects.filter(tag_id=tag_id).first()
            if not tag:
                return Response(
                    {"success": False, "error": "Tag not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            tag.status = tag_status
            tag.save()
            return Response(
                {
                    "success": True,
                    "message": "Status updated",
                    "data": {
                        "tag_id": tag.tag_id,
                        "art_no": tag.art_no.art_no,
                        "status": tag.status,
                    },
                },
                status=status.HTTP_200_OK,
            )

    @extend_schema(
        summary="Tag löschen",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "tag_id": {"type": "string"},
                },
                "required": ["tag_id"],
            }
        },
        responses={
            204: {"description": "Tag deleted"},
            400: {
                "description": "Bad Request",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string"},
                            },
                        }
                    }
                },
            },
            404: {
                "description": "Tag not found",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string"},
                            },
                        }
                    }
                },
            },
        },
        tags=["Tags"],
    )
    def delete(self, request):
        body = request.data or {}
        tag_id = body.get("tag_id")

        if not tag_id:
            return Response(
                {"success": False, "error": "tag_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tag = Tags.objects.filter(tag_id=tag_id).first()
        if not tag:
            return Response(
                {"success": False, "error": "Tag not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
