from django.test import SimpleTestCase

from .forms import AddClientForm, ClientUpdateForm, _pop_field_name
from .models import Client


class ClientPopFormTests(SimpleTestCase):
    def test_add_form_contains_all_model_pop_choices(self):
        form = AddClientForm()

        for pop_value, pop_label in Client.POP_CHOICES:
            field_name = _pop_field_name(pop_value)
            self.assertIn(field_name, form.fields)
            self.assertEqual(form.fields[field_name].label, pop_label)

    def test_datanet_pop_is_preselected_on_update_form(self):
        client = Client(
            client_type=Client.COMPANY,
            name="Example Client",
            contact_person="Jane Doe",
            primary_email="jane@example.com",
            secondary_email="ops@example.com",
            phone_number="+254700123456",
        )
        client.set_pops([Client.POP_DATANET_UG])
        client.pk = 1

        self.assertIn(Client.POP_DATANET_UG, client.get_pops())

        update_form = ClientUpdateForm(instance=client)
        self.assertTrue(update_form.fields["pop_datanet_ug"].initial)
