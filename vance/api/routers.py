from .gmail import _router as gmail_router
from .webhooks import _router as tool_webhooks_router
from .whatsapp import _router as whatsapp_router
from .public_profiles import router as public_profiles_router
from .job_application_routes import router as job_application_router
from .candidate_onboarding_routes import router as candidate_onboarding_router
from .candidate_profile_routes import router as candidate_profile_router
from .switch_routes import router as switch_router
from .switch_practice_routes import router as switch_practice_router
from .switch_business_routes import router as switch_business_router
from .switch_metrics_routes import router as switch_metrics_router
from .community_routes import router as community_router
from .community_seed_routes import router as community_seed_router
from .community_auto_comment_route import router as community_auto_comment_router
from .vobiz_routes import router as vobiz_router
from .vobiz_bridge import router as vobiz_bridge_router
from .live_connect_routes import router as live_connect_router
from .live_connect_bridge import router as live_connect_bridge_router
from .employer_outbound_routes import router as employer_outbound_router
from .employer_outbound_bridge import router as employer_outbound_bridge_router
from .sales_outbound_routes import router as sales_outbound_router
from .sales_outbound_bridge import router as sales_outbound_bridge_router
from .employer_match_routes import router as employer_match_router
from .employer_match_routes import hire_router
from .switch_whatsapp_routes import router as switch_wa_router
from .switch_placement_routes import router as switch_placement_router
from .switch_placement_routes import pages_router as switch_placement_pages_router
from .switch_booking_routes import router as switch_booking_router
from .switch_payment_routes import router as switch_payment_router
from .switch_payment_routes import pages_router as switch_payment_pages_router
from .sms_tracking_routes import router as sms_tracking_router
from .worker_profiles_routes import router as worker_profiles_router
from .admin_notifications_routes import router as admin_notifications_router
from .wa_blast_routes import router as wa_blast_router

routers = [whatsapp_router, tool_webhooks_router, gmail_router, public_profiles_router, job_application_router, candidate_onboarding_router, candidate_profile_router, switch_router, switch_practice_router, switch_business_router, switch_metrics_router, community_router, community_seed_router, community_auto_comment_router, vobiz_router, vobiz_bridge_router, live_connect_router, live_connect_bridge_router, employer_outbound_router, employer_outbound_bridge_router, sales_outbound_router, sales_outbound_bridge_router, employer_match_router, hire_router, switch_wa_router, switch_placement_router, switch_placement_pages_router, switch_booking_router, switch_payment_router, switch_payment_pages_router, sms_tracking_router, worker_profiles_router, admin_notifications_router, wa_blast_router]
