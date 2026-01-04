"""API Views for KanbanAPI.

Clean endpoints returning flat JSON consistently:
{"success": true, "data": ...} or {"success": false, "error": "..."}
"""

from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from api.models import Article, Tags, OrderProposal

import secrets
import string


class ArticlesView(APIView):
    """Resource-stable /api/articles/ endpoint.
    GET: list all articles
    POST: create or update article (action in body)
    """

    @extend_schema(
        summary="Liste aller Artikel",
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search in Article Number or Description",
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
                            "kanban_min": serializers.IntegerField(),
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

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(art_no__icontains=search))

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
                "kanban_min": a.kanban_min,
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
                            "art_supplier": serializers.CharField(),
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
                "art_supplier": t.art_no.art_supplier,
                "created_at": t.created_at,
            }
            for t in qs
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Tag anlegen, aktualisieren, Status setzen, generieren oder suchen",
        request=inline_serializer(
            name="TagActionRequest",
            fields={
                "action": serializers.ChoiceField(
                    choices=["create", "update", "set_status", "generate", "search"]
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

        if not action or action not in [
            "create",
            "update",
            "set_status",
            "generate",
            "search",
        ]:
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

            # Handle multiple tag_ids separated by ;
            tag_ids = [t.strip() for t in tag_id.split(";") if t.strip()]

            if not tag_ids:
                return Response(
                    {"success": False, "error": "No valid tag_id provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            updated_tags = []
            not_found_tags = []

            # Fetch all tags at once
            tags = Tags.objects.filter(tag_id__in=tag_ids)
            tags_dict = {tag.tag_id: tag for tag in tags}

            for tid in tag_ids:
                tag = tags_dict.get(tid)
                if not tag:
                    not_found_tags.append(tid)
                    continue

                tag.status = tag_status
                tag.save()
                updated_tags.append(
                    {
                        "tag_id": tag.tag_id,
                        "art_no": tag.art_no.art_no,
                        "status": tag.status,
                    }
                )

            if not updated_tags:
                return Response(
                    {
                        "success": False,
                        "error": f"Tags not found: {', '.join(not_found_tags)}",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Return list if multiple IDs were requested or if semicolon was present
            if ";" in tag_id or len(tag_ids) > 1:
                return Response(
                    {
                        "success": True,
                        "message": f"Status updated for {len(updated_tags)} tags",
                        "data": updated_tags,
                        "not_found": not_found_tags if not_found_tags else None,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": True,
                        "message": "Status updated",
                        "data": updated_tags[0],
                    },
                    status=status.HTTP_200_OK,
                )

        elif action == "search":
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
            return Response(
                {
                    "success": True,
                    "message": "Searched tag",
                    "data": {
                        "tag_id": tag.tag_id,
                        "art_no": tag.art_no.art_no,
                        "description": tag.art_no.description,
                        "status": tag.status,
                        "art_supplier": tag.art_no.art_supplier,
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


class OrderProposalView(APIView):
    """Resource-stable /api/order-proposals/ endpoint.
    GET: list all order proposals with optional status filter
    PATCH: update proposal status
    """

    @extend_schema(
        summary="Liste aller Bestellvorschläge",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Filter by status",
                required=False,
                type=str,
                enum=["NEU", "GEPRÜFT", "FREIGEGEBEN", "VERWORFEN", "GEMELDET"],
            ),
        ],
        responses={
            200: inline_serializer(
                name="OrderProposalListResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "data": inline_serializer(
                        name="OrderProposalData",
                        fields={
                            "proposal_id": serializers.IntegerField(),
                            "lieferant": serializers.CharField(),
                            "artikelnummer": serializers.CharField(),
                            "beschreibung": serializers.CharField(),
                            "kanbanGesamt": serializers.IntegerField(),
                            "anwesend": serializers.IntegerField(),
                            "bereitsGemeldet": serializers.IntegerField(),
                            "fehlmenge": serializers.IntegerField(),
                            "status": serializers.CharField(),
                            "updatedAt": serializers.DateTimeField(),
                        },
                        many=True,
                    ),
                },
            )
        },
        tags=["OrderProposals"],
    )
    def get(self, request):
        """List all order proposals with optional status filter"""
        qs = OrderProposal.objects.all()

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        data = [
            {
                "proposal_id": p.id,
                "lieferant": p.lieferant,
                "artikelnummer": p.artikelnummer,
                "beschreibung": p.beschreibung,
                "kanbanGesamt": p.kanbanGesamt,
                "anwesend": p.anwesend,
                "bereitsGemeldet": p.bereitsGemeldet,
                "fehlmenge": p.fehlmenge,
                "status": p.status,
                "updatedAt": p.updated_at,
            }
            for p in qs
        ]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Bestellvorschlag Status aktualisieren",
        request=inline_serializer(
            name="OrderProposalUpdateRequest",
            fields={
                "proposal_id": serializers.IntegerField(),
                "status": serializers.ChoiceField(
                    choices=["NEU", "GEPRÜFT", "FREIGEGEBEN", "VERWORFEN", "GEMELDET"]
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="OrderProposalUpdateResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "proposal_id": serializers.IntegerField(),
                    "status": serializers.CharField(),
                },
            ),
            400: inline_serializer(
                name="OrderProposalErrorResponse400",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
            404: inline_serializer(
                name="OrderProposalErrorResponse404",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
        },
        tags=["OrderProposals"],
    )
    def patch(self, request):
        """Update proposal status with validation for allowed transitions"""
        body = request.data or {}
        proposal_id = body.get("proposal_id")
        new_status = body.get("status")

        if not proposal_id or not new_status:
            return Response(
                {"success": False, "error": "proposal_id and status are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate status value
        valid_statuses = ["NEU", "GEPRÜFT", "FREIGEGEBEN", "VERWORFEN", "GEMELDET"]
        if new_status not in valid_statuses:
            return Response(
                {"success": False, "error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find proposal
        try:
            proposal = OrderProposal.objects.get(id=proposal_id)
        except OrderProposal.DoesNotExist:
            return Response(
                {"success": False, "error": "Proposal not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate and update status using model method
        if not proposal.can_transition_to(new_status):
            return Response(
                {
                    "success": False,
                    "error": f"Invalid transition from {proposal.status} to {new_status}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update status
        try:
            proposal.update_status(new_status)
        except ValueError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"success": True, "proposal_id": proposal.id, "status": proposal.status},
            status=status.HTTP_200_OK,
        )


class OrderProposalSendView(APIView):
    """Send order proposals endpoint: POST /api/order-proposals/send/"""

    @extend_schema(
        summary="Bestellvorschläge senden (Sammelaktion)",
        request=inline_serializer(
            name="OrderProposalSendRequest",
            fields={
                "supplier": serializers.CharField(),
                "proposal_ids": serializers.ListField(child=serializers.IntegerField()),
            },
        ),
        responses={
            200: inline_serializer(
                name="OrderProposalSendResponse",
                fields={
                    "success": serializers.BooleanField(default=True),
                    "sent": serializers.ListField(child=serializers.IntegerField()),
                    "failed": serializers.ListField(
                        child=inline_serializer(
                            name="FailedProposal",
                            fields={
                                "id": serializers.IntegerField(),
                                "reason": serializers.CharField(),
                            },
                        )
                    ),
                },
            ),
            400: inline_serializer(
                name="OrderProposalSendErrorResponse400",
                fields={
                    "success": serializers.BooleanField(default=False),
                    "error": serializers.CharField(),
                },
            ),
        },
        tags=["OrderProposals"],
    )
    def post(self, request):
        """Send order proposals for a specific supplier (batch action)"""
        body = request.data or {}
        supplier = body.get("supplier")
        proposal_ids = body.get("proposal_ids", [])

        if not supplier:
            return Response(
                {"success": False, "error": "supplier is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not proposal_ids or not isinstance(proposal_ids, list):
            return Response(
                {"success": False, "error": "proposal_ids must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch proposals with status FREIGEGEBEN
        proposals = OrderProposal.objects.filter(
            id__in=proposal_ids,
            status=OrderProposal.STATUS_FREIGEGEBEN,
            lieferant=supplier,
        )

        sent = []
        failed = []

        for proposal in proposals:
            try:
                # TODO: Implement actual CSV generation and sending logic here
                # For now, we'll simulate success
                # Example: generate_csv_and_send(proposal)

                # Update status to GEMELDET
                proposal.status = OrderProposal.STATUS_GEMELDET
                proposal.save()
                sent.append(proposal.id)

            except Exception as e:
                # Keep status as FREIGEGEBEN on failure
                failed.append({"id": proposal.id, "reason": str(e)})

        # Check for proposals that were not found or had wrong status
        found_ids = {p.id for p in proposals}
        for pid in proposal_ids:
            if pid not in found_ids:
                # Check if it exists but wrong status/supplier
                try:
                    p = OrderProposal.objects.get(id=pid)
                    if p.status != OrderProposal.STATUS_FREIGEGEBEN:
                        failed.append(
                            {"id": pid, "reason": f"Status is {p.status}, not FREIGEGEBEN"}
                        )
                    elif p.lieferant != supplier:
                        failed.append(
                            {"id": pid, "reason": f"Supplier mismatch: {p.lieferant}"}
                        )
                except OrderProposal.DoesNotExist:
                    failed.append({"id": pid, "reason": "Proposal not found"})

        return Response(
            {"success": True, "sent": sent, "failed": failed},
            status=status.HTTP_200_OK,
        )

