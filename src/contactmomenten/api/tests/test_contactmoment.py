from datetime import datetime

from django.utils.timezone import make_aware

from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.tests import JWTAuthMixin, get_validation_errors, reverse

from contactmomenten.datamodel.constants import InitiatiefNemer
from contactmomenten.datamodel.models import ContactMoment
from contactmomenten.datamodel.tests.factories import (
    ContactMomentFactory,
    MedewerkerFactory,
)

KLANT = "http://klanten.nl/api/v1/klanten/12345"


class ContactMomentTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_list_contactmomenten(self):
        list_url = reverse(ContactMoment)
        ContactMomentFactory.create_batch(2)

        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 2)

    def test_read_contactmoment(self):
        contactmoment = ContactMomentFactory.create(
            interactiedatum=make_aware(datetime(2019, 1, 1)),
            initiatiefnemer=InitiatiefNemer.gemeente,
        )
        detail_url = reverse(contactmoment)

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{detail_url}",
                "vorigContactmoment": None,
                "volgendContactmoment": None,
                "bronorganisatie": contactmoment.bronorganisatie,
                "klant": contactmoment.klant,
                "interactiedatum": "2019-01-01T00:00:00Z",
                "kanaal": contactmoment.kanaal,
                "voorkeurskanaal": contactmoment.voorkeurskanaal,
                "voorkeurstaal": contactmoment.voorkeurstaal,
                "tekst": contactmoment.tekst,
                "onderwerpLinks": [],
                "initiatiefnemer": InitiatiefNemer.gemeente,
                "medewerker": contactmoment.medewerker,
                "medewerkerIdentificatie": None,
            },
        )

    def test_read_contactmoment_with_medewerker(self):
        contactmoment = ContactMomentFactory.create(
            interactiedatum=make_aware(datetime(2019, 1, 1)),
            initiatiefnemer=InitiatiefNemer.gemeente,
            medewerker="",
            voorkeurstaal="nld",
        )
        medewerker = MedewerkerFactory.create(contactmoment=contactmoment)
        detail_url = reverse(contactmoment)

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            {
                "url": f"http://testserver{detail_url}",
                "vorigContactmoment": None,
                "volgendContactmoment": None,
                "bronorganisatie": contactmoment.bronorganisatie,
                "klant": contactmoment.klant,
                "interactiedatum": "2019-01-01T00:00:00Z",
                "kanaal": contactmoment.kanaal,
                "voorkeurskanaal": contactmoment.voorkeurskanaal,
                "voorkeurstaal": contactmoment.voorkeurstaal,
                "tekst": contactmoment.tekst,
                "onderwerpLinks": [],
                "initiatiefnemer": InitiatiefNemer.gemeente,
                "medewerker": "",
                "medewerkerIdentificatie": {
                    "identificatie": medewerker.identificatie,
                    "achternaam": medewerker.achternaam,
                    "voorletters": medewerker.voorletters,
                    "voorvoegselAchternaam": medewerker.voorvoegsel_achternaam,
                },
            },
        )

    def test_create_contactmoment(self):
        list_url = reverse(ContactMoment)
        data = {
            "bronorganisatie": "423182687",
            "klant": KLANT,
            "kanaal": "telephone",
            "tekst": "some text",
            "onderwerpLinks": [],
            "initiatiefnemer": InitiatiefNemer.gemeente,
            "medewerker": "http://example.com/medewerker/1",
        }

        response = self.client.post(list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contactmoment = ContactMoment.objects.get()

        self.assertEqual(contactmoment.klant, KLANT)
        self.assertEqual(contactmoment.kanaal, "telephone")
        self.assertEqual(contactmoment.tekst, "some text")
        self.assertEqual(contactmoment.initiatiefnemer, InitiatiefNemer.gemeente)
        self.assertEqual(contactmoment.medewerker, "http://example.com/medewerker/1")

    def test_create_contactmoment_with_medewerker(self):
        list_url = reverse(ContactMoment)
        data = {
            "bronorganisatie": "423182687",
            "klant": KLANT,
            "kanaal": "telephone",
            "tekst": "some text",
            "onderwerpLinks": [],
            "initiatiefnemer": InitiatiefNemer.gemeente,
            "medewerkerIdentificatie": {
                "identificatie": "12345",
                "achternaam": "Buurman",
                "voorletters": "B B",
            },
        }

        response = self.client.post(list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contactmoment = ContactMoment.objects.get()

        self.assertEqual(contactmoment.klant, KLANT)
        self.assertEqual(contactmoment.kanaal, "telephone")
        self.assertEqual(contactmoment.tekst, "some text")
        self.assertEqual(contactmoment.initiatiefnemer, InitiatiefNemer.gemeente)

        medewerker = contactmoment.medewerker_identificatie

        self.assertEqual(medewerker.identificatie, "12345")
        self.assertEqual(medewerker.achternaam, "Buurman")
        self.assertEqual(medewerker.voorletters, "B B")

    def test_create_contactmoment_fail_no_medewerker(self):
        list_url = reverse(ContactMoment)
        data = {
            "bronorganisatie": "423182687",
            "klant": KLANT,
            "kanaal": "telephone",
            "tekst": "some text",
            "initiatiefnemer": InitiatiefNemer.gemeente,
        }

        response = self.client.post(list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")

        self.assertEqual(error["code"], "invalid-medewerker")

    def test_create_contactmoment_vorig_contactmoment(self):
        vorig_cmc = ContactMomentFactory.create()
        list_url = reverse(ContactMoment)
        data = {
            "bronorganisatie": "423182687",
            "kanaal": "telephone",
            "tekst": "some text",
            "onderwerpLinks": [],
            "initiatiefnemer": InitiatiefNemer.gemeente,
            "medewerker": "http://example.com/medewerker/1",
            "vorigContactmoment": reverse(vorig_cmc),
        }

        response = self.client.post(list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contactmoment = ContactMoment.objects.last()

        self.assertEqual(contactmoment.kanaal, "telephone")
        self.assertEqual(contactmoment.tekst, "some text")
        self.assertEqual(contactmoment.initiatiefnemer, InitiatiefNemer.gemeente)
        self.assertEqual(contactmoment.medewerker, "http://example.com/medewerker/1")
        self.assertEqual(contactmoment.vorig_contactmoment, vorig_cmc)

        # Check if volgendContactmoment is set correctly

        response = self.client.get(reverse(vorig_cmc))

        self.assertEqual(
            response.data["volgend_contactmoment"],
            f"http://testserver{reverse(contactmoment)}",
        )

        vorig_cmc.refresh_from_db()
        self.assertEqual(vorig_cmc.volgend_contactmoment, contactmoment)

    def test_update_contactmoment(self):
        contactmoment = ContactMomentFactory.create()
        detail_url = reverse(contactmoment)

        response = self.client.patch(detail_url, {"klant": KLANT})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contactmoment.refresh_from_db()

        self.assertEqual(contactmoment.klant, KLANT)

    def test_update_contactmoment_with_medewerker(self):
        contactmoment = ContactMomentFactory.create()
        detail_url = reverse(contactmoment)
        data = {
            "medewerker": "",
            "medewerkerIdentificatie": {
                "identificatie": "12345",
                "achternaam": "Buurman",
                "voorletters": "B B",
            },
        }

        response = self.client.patch(detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contactmoment.refresh_from_db()

        self.assertEqual(contactmoment.medewerker, "")

        medewerker = contactmoment.medewerker_identificatie

        self.assertEqual(medewerker.identificatie, "12345")
        self.assertEqual(medewerker.achternaam, "Buurman")
        self.assertEqual(medewerker.voorletters, "B B")

    def test_update_contactmoment_override_vorig_contactmoment(self):
        vorig_cmc = ContactMomentFactory.create()
        contactmoment = ContactMomentFactory.create(vorig_contactmoment=vorig_cmc)

        new_vorig_cmc = ContactMomentFactory.create()

        detail_url = reverse(contactmoment)
        data = {"vorigContactmoment": reverse(new_vorig_cmc)}

        response = self.client.patch(detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        vorig_cmc.refresh_from_db()
        contactmoment.refresh_from_db()
        new_vorig_cmc.refresh_from_db()

        self.assertEqual(contactmoment.vorig_contactmoment, new_vorig_cmc)
        self.assertEqual(new_vorig_cmc.volgend_contactmoment, contactmoment)

    def test_destroy_contactmoment(self):
        contactmoment = ContactMomentFactory.create()
        detail_url = reverse(contactmoment)

        response = self.client.delete(detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ContactMoment.objects.count(), 0)


class ContactMomentFilterTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True
    list_url = reverse(ContactMoment)

    def test_filter_voorkeurstaal(self):
        ContactMomentFactory.create(voorkeurstaal="nld")
        ContactMomentFactory.create(voorkeurstaal="eng")

        response = self.client.get(
            self.list_url, {"voorkeurstaal": "nld"}, HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["voorkeurstaal"], "nld",
        )

    def test_list_contactmomenten_filter_vorig_contactmoment(self):
        list_url = reverse(ContactMoment)
        cmc1, cmc2, cmc3 = ContactMomentFactory.create_batch(3)
        cmc3.vorig_contactmoment = cmc2
        cmc3.save()

        response = self.client.get(
            list_url,
            {"vorigContactmoment": f"http://testserver.com{reverse(cmc2)}"},
            HTTP_HOST="testserver.com",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)

    def test_list_contactmomenten_filter_volgend_contactmoment(self):
        list_url = reverse(ContactMoment)
        cmc1, cmc2, cmc3 = ContactMomentFactory.create_batch(3)
        cmc3.vorig_contactmoment = cmc2
        cmc3.save()

        response = self.client.get(
            list_url,
            {"volgendContactmoment": f"http://testserver.com{reverse(cmc3)}"},
            HTTP_HOST="testserver.com",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
