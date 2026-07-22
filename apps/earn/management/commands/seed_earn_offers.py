from django.core.management.base import BaseCommand

from apps.earn.models import QuickCashOffer

DEFAULT_OFFERS = [
    {
        'title': 'Jumia Phone Accessories',
        'description': 'Sell chargers, earbuds & cases',
        'earning_range': '₵80 – ₵650',
        'link': 'https://www.jumia.com.gh/catalog/?q=phone+accessories',
        'offer_type': 'affiliate',
    },
    {
        'title': 'Jiji Ghana Marketplace',
        'description': 'Sell used items instantly',
        'earning_range': '₵300 – ₵2,500',
        'link': 'https://jiji.com.gh',
        'offer_type': 'affiliate',
    },
    {
        'title': 'Sagapoll Surveys',
        'description': 'Answer quick surveys',
        'earning_range': '₵50 – ₵220/mo',
        'link': 'https://www.sagapoll.com',
        'offer_type': 'survey',
    },
    {
        'title': 'Fiverr Data Entry',
        'description': 'Offer simple online tasks',
        'earning_range': '₵400 – ₵1,800',
        'link': 'https://www.fiverr.com',
        'offer_type': 'affiliate',
    },
    {
        'title': 'Selar Digital Products',
        'description': 'Sell eBooks & printables',
        'earning_range': '₵150 – ₵900',
        'link': 'https://selar.com',
        'offer_type': 'affiliate',
    },
]


class Command(BaseCommand):
    help = 'Seeds the default official Quick Cash partner offers (safe to re-run).'

    def handle(self, *args, **options):
        created = 0
        for data in DEFAULT_OFFERS:
            _, was_created = QuickCashOffer.objects.get_or_create(
                title=data['title'], submitted_by=None, defaults=data
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(f'Seeded {created} new Quick Cash offer(s) (of {len(DEFAULT_OFFERS)} checked).')
        )
