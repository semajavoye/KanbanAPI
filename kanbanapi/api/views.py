"""API Views for KanbanAPI.

Clean endpoints returning flat JSON consistently:
{"success": true, "data": ...} or {"success": false, "error": "..."}
"""

from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import status, serializers
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
    """

    @extend_schema(
        summary="Liste aller Artikel",
        parameters=[
            OpenApiParameter(
                name="art_no",
                description="Filter by Article Number",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="art_supplier",
                description="Filter by Supplier",
                required=False,
                type=str,
                enum=["OKB", "RKB", "SW"],
            ),
        ],
        responses={
            200: inline_serializer(
                name="ArticleListResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "data": inline_serializer(
                        name="ArticleData",
                        fields={
                            "art_no": serializers.CharField(),
                            "art_supplier": serializers.ChoiceField(
                                choices=["OKB", "RKB", "SW"]
                            ),
                            "description": serializers.CharField(),
                        },
                        many=True,
                    ),
                },
            )
        },
        tags=["Articles"],
    )
    def get(self, request):
        qs = Article.objects.all().only("art_no", "art_supplier", "description")

        art_no = request.query_params.get("art_no")
        if art_no:
            qs = qs.filter(art_no__icontains=art_no)

        art_supplier = request.query_params.get("art_supplier")
        if art_supplier:
            qs = qs.filter(art_supplier=art_supplier)

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
        request=inline_serializer(
            name="ArticleUpdateRequest",
            fields={
                "action": serializers.ChoiceField(choices=["update"]),
                "data": inline_serializer(
                    name="ArticleUpdateData",
                    fields={
                        "art_no": serializers.CharField(),
                        "art_supplier": serializers.ChoiceField(
                            choices=["OKB", "RKB", "SW"]
                        ),
                    },
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="ArticleUpdateResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="ArticleUpdateResponseData",
                        fields={
                            "art_no": serializers.CharField(),
                            "art_supplier": serializers.CharField(),
                            "description": serializers.CharField(),
                        },
                    ),
                },
            ),
            400: inline_serializer(
                name="ErrorResponse400",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
            404: inline_serializer(
                name="ErrorResponse404",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
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
        parameters=[
            OpenApiParameter(
                name="tag_id",
                description="Filter by Tag ID",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="art_no",
                description="Filter by Article Number",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="status",
                description="Filter by Status (0 or 1)",
                required=False,
                type=int,
                enum=[0, 1],
            ),
        ],
        responses={
            200: inline_serializer(
                name="TagListResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "data": inline_serializer(
                        name="TagData",
                        fields={
                            "tag_id": serializers.CharField(),
                            "art_no": serializers.CharField(),
                            "description": serializers.CharField(),
                            "status": serializers.IntegerField(),
                            "created_at": serializers.DateTimeField(),
                        },
                        many=True,
                    ),
                },
            )
        },
        tags=["Tags"],
    )
    def get(self, request):
        qs = Tags.objects.select_related("art_no").only(
            "tag_id", "art_no__art_no", "art_no__description", "status", "created_at"
        )

        tag_id = request.query_params.get("tag_id")
        if tag_id:
            qs = qs.filter(tag_id__icontains=tag_id)

        art_no = request.query_params.get("art_no")
        if art_no:
            qs = qs.filter(art_no__art_no__icontains=art_no)

        status_param = request.query_params.get("status")
        if status_param is not None:
            try:
                qs = qs.filter(status=int(status_param))
            except ValueError:
                pass

        data = [
            {
                "tag_id": t.tag_id,
                "art_no": t.art_no.art_no,
                "description": t.art_no.description,
                "status": t.status,
                "created_at": t.created_at,
            }
            for t in qs
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Tag anlegen, aktualisieren, Status setzen oder generieren",
        request=inline_serializer(
            name="TagActionRequest",
            fields={
                "action": serializers.ChoiceField(
                    choices=["create", "update", "set_status", "generate"]
                ),
                "data": inline_serializer(
                    name="TagActionData",
                    fields={
                        "tag_id": serializers.CharField(required=False),
                        "art_no": serializers.CharField(required=False),
                        "status": serializers.ChoiceField(
                            choices=[0, 1], required=False
                        ),
                        "preferred_tag_id": serializers.CharField(required=False),
                    },
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="TagActionResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "message": serializers.CharField(),
                    "data": inline_serializer(
                        name="TagActionResponseData",
                        fields={
                            "tag_id": serializers.CharField(required=False),
                            "art_no": serializers.CharField(required=False),
                            "status": serializers.IntegerField(required=False),
                        },
                    ),
                },
            ),
            400: inline_serializer(
                name="TagErrorResponse400",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
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
        request=inline_serializer(
            name="TagDeleteRequest",
            fields={
                "tag_ids": serializers.CharField(
                    help_text="Semicolon separated list of tag IDs"
                )
            },
        ),
        responses={
            200: inline_serializer(
                name="TagDeleteResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "message": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                name="TagDeleteErrorResponse400",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
            404: inline_serializer(
                name="TagDeleteErrorResponse404",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
        },
        tags=["Tags"],
    )
    def delete(self, request):
        body = request.data or {}
        tag_ids = body.get("tag_ids")

        if not tag_ids:
            return Response(
                {"success": False, "error": "tag_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Split tag_ids by semicolon and strip whitespace
        tag_id_list = [tid.strip() for tid in tag_ids.split(";") if tid.strip()]

        if not tag_id_list:
            return Response(
                {"success": False, "error": "No valid tag_ids provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find all matching tags
        tags = Tags.objects.filter(tag_id__in=tag_id_list)

        if not tags.exists():
            return Response(
                {"success": False, "error": "No tags found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete all found tags
        deleted_count = tags.count()
        tags.delete()

        return Response(
            {"success": True, "message": f"{deleted_count} tag(s) deleted"},
            status=status.HTTP_200_OK,
        )
