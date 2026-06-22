from __future__ import annotations

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.community.models import AgoraComment, AgoraPost


SEED_PREFIXES = ("agora_seed_",)

AUTHORS = [
    ("minahome", "민아"),
    ("jun_zip", "준호"),
    ("sujeonglog", "수정"),
    ("taewon82", "태원"),
    ("yerin_note", "예린"),
    ("dongmin77", "동민"),
    ("hana_plan", "하나"),
    ("jaehoon_k", "재호"),
]

POSTS = {
    "notice": [
        ("공공분양이랑 신혼희망타운 같이 봐도 될까요?", "조건은 비슷해 보이는데 실제로 준비해야 하는 서류가 조금씩 달라서 헷갈리네요. 당첨 후 자금 일정까지 같이 보신 분 있나요?"),
        ("사전청약 넣었던 분들 본청약 때 뭐부터 확인하세요?", "지역 우선이랑 무주택 기준은 다시 봤는데, 소득 기준이 월평균인지 전년도 기준인지 매번 헷갈립니다."),
        ("마감일 가까운 공고는 우선순위 낮춰도 될까요?", "급하게 넣었다가 자금계획이 안 맞을까봐 걱정입니다. 점수가 높아도 준비가 안 되면 넘기는 게 맞을지 고민돼요."),
        ("청약통장 납입 인정회차 확인 어디서 하세요?", "은행 앱에서 보는 숫자랑 공고문에서 말하는 인정 기준이 미묘하게 달라 보여서 공식 확인 방법이 궁금합니다."),
        ("특별공급 조건 체크리스트 공유해요", "제가 보는 순서는 무주택, 소득, 자산, 거주기간, 청약통장 순서입니다. 빠뜨리기 쉬운 항목 있으면 알려주세요."),
        ("분양가 0원으로 보이는 공고는 어떻게 판단하세요?", "간혹 가격 정보가 아직 비어 있는 공고가 있어서 실제 모집공고 PDF까지 열어봐야 하더라고요."),
        ("지역 우선 조건 때문에 고민입니다", "주소지는 경기인데 관심 단지는 서울이라 배점이 크게 밀릴지 모르겠네요. 비슷한 상황이신 분 계신가요?"),
        ("공고 PDF에서 제일 먼저 보는 항목", "저는 주택형, 공급금액, 계약금, 전매제한을 먼저 봅니다. 다들 어떤 항목을 먼저 확인하시나요?"),
    ],
    "product": [
        ("적금 금리는 높아도 기간이 짧으면 애매하네요", "계약금 모으는 용도로는 6개월보다 12개월 이상이 낫다고 느꼈습니다. 중도해지 조건도 꼭 봐야겠어요."),
        ("예금이랑 적금 중 계약금 준비는 뭐가 나을까요?", "목돈이 조금 있으면 예금, 매달 모으는 중이면 적금으로 나누는 게 맞는지 의견 듣고 싶습니다."),
        ("우대금리 조건 너무 복잡한 상품은 걸러도 될까요?", "급여이체, 카드실적, 앱 로그인까지 다 챙기기 어렵더라고요. 실수령 금리 기준으로 보는 게 맞겠죠?"),
        ("금융상품 후보랑 자금로드맵 후보 차이", "상품 목록에서 좋아 보이는 것과 로드맵에서 추천되는 게 달라서 기준을 같이 비교해보고 있습니다."),
        ("주택담보대출은 금리보다 상환방식이 먼저인가요?", "분할상환이 안정적이긴 한데 초기 부담이 커서 청약 자금 계획과 같이 봐야 할 것 같습니다."),
        ("청년 우대형 상품 아직 쓸만한가요?", "조건에 맞으면 금리보다 비과세나 혜택이 더 중요할 때가 있더라고요."),
        ("은행별 같은 이름 상품도 옵션이 다르네요", "기간별 금리가 달라서 목록만 보고 판단하면 놓치는 게 꽤 있었습니다."),
    ],
    "funding": [
        ("계약금 부족액 700만원 정도면 어떻게 메우세요?", "월 저축으로는 조금 빠듯해서 예금 일부 해지와 단기 적금을 같이 고민 중입니다."),
        ("입주 전까지 현금 흐름표 만들어봤습니다", "계약금, 중도금, 잔금이 한눈에 보이니까 불안이 줄긴 하네요. 변수는 대출 심사 기간입니다."),
        ("계약 직전 카드값 정리하는 게 좋겠죠?", "DSR이나 심사에 직접 영향이 있는지는 모르겠지만 고정지출을 줄여두는 게 마음 편할 것 같습니다."),
        ("중도금 대출 가능 여부는 어디까지 믿어도 될까요?", "공고문에는 가능하다고 나오지만 개인 신용이나 소득에 따라 다를 수 있어서 은행 상담도 필요해 보입니다."),
        ("계약금 준비 목표를 너무 빡빡하게 잡았나 봅니다", "비상금까지 다 넣으면 위험해서 최소 생활비는 남기는 쪽으로 다시 계산 중입니다."),
        ("자금 로드맵에서 월 목표가 높게 나오면", "기간을 늘릴 수 없으면 후보를 바꾸는 게 맞을까요? 무리해서 넣는 건 피하고 싶습니다."),
        ("잔금 시점까지 소득 증빙 준비", "재직증명서, 원천징수, 건강보험 납부확인서 같은 서류를 미리 모아두고 있습니다."),
        ("부모님 지원금은 자금계획에 어떻게 적나요?", "증여나 차용증 이슈가 있어서 단순히 현금으로만 보면 안 될 것 같습니다."),
    ],
    "free": [
        ("지도에서 은행 경로 보는 기능 꽤 유용하네요", "실제로 상담 갈 은행을 지도에서 바로 보는 흐름이 발표 때도 이해하기 쉬워 보입니다."),
        ("공고가 너무 많을 때 기준을 어떻게 잡으세요?", "지역, 가격, 마감일 순으로 줄이니 조금 낫긴 한데 여전히 선택지가 많네요."),
        ("청약 준비하면서 제일 귀찮은 것", "저는 서류 이름이 비슷비슷한 게 제일 어렵습니다. 주민등록초본이랑 등본부터 매번 헷갈려요."),
        ("경제 NOW에서 부동산 지표 보는 맛이 있네요", "청약이랑 직접 연결되는 숫자부터 보이니까 금은 같은 지표는 아래에 있는 게 더 자연스러워요."),
        ("처음 준비하는 사람에게 제일 필요한 화면", "개인적으로는 조건 입력보다 대시보드가 먼저 이해돼야 계속 쓰게 되는 것 같습니다."),
        ("관심 공고 저장 기준", "당장 넣을 공고만 저장할지, 비교용으로 넓게 저장할지 고민됩니다."),
    ],
}

COMMENTS = [
    "저도 이 부분 때문에 공고문을 두 번씩 확인하고 있어요.",
    "은행 상담 예약 전에 체크리스트로 정리해두면 덜 헷갈립니다.",
    "마감일만 보고 급하게 움직이면 놓치는 게 생기더라고요.",
    "조건이 맞아도 자금 일정이 안 맞으면 과감히 제외하는 편입니다.",
    "비슷한 상황인데 저는 공식 공고 기준으로만 판단하려고요.",
    "좋은 포인트네요. 저도 저장해두고 비교해봐야겠습니다.",
    "서류는 미리 발급 가능 여부부터 보는 게 마음 편했습니다.",
    "이건 사람마다 달라서 월 저축 가능액을 먼저 봐야 할 것 같아요.",
]


class Command(BaseCommand):
    help = "Seed realistic Agora posts and comments for presentation."

    def add_arguments(self, parser):
        parser.add_argument("--posts-per-category", type=int, default=8)
        parser.add_argument("--seed", type=int, default=20260623)

    def handle(self, *args, **options):
        random.seed(options["seed"])
        per_category = min(10, max(6, options["posts_per_category"]))
        user_model = get_user_model()

        authors = []
        for username, first_name in AUTHORS:
            user, _created = user_model.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com", "first_name": first_name},
            )
            if not user.has_usable_password():
                user.set_password("firsthome123!")
                user.save(update_fields=["password"])
            authors.append(user)

        seed_usernames = [username for username, _name in AUTHORS]
        AgoraComment.objects.filter(author__username__in=seed_usernames).delete()
        AgoraPost.objects.filter(author__username__in=seed_usernames).delete()
        for prefix in SEED_PREFIXES:
            AgoraComment.objects.filter(author__username__startswith=prefix).delete()
            AgoraPost.objects.filter(author__username__startswith=prefix).delete()

        post_count = 0
        comment_count = 0
        for category, candidates in POSTS.items():
            category_count = min(per_category, len(candidates))
            for title, content in random.sample(candidates, category_count):
                post = AgoraPost.objects.create(
                    author=random.choice(authors),
                    category=category,
                    title=title,
                    content=content,
                )
                post_count += 1
                for comment_text in random.sample(COMMENTS, random.randint(0, 4)):
                    AgoraComment.objects.create(post=post, author=random.choice(authors), content=comment_text)
                    comment_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {post_count} Agora posts and {comment_count} comments."))
