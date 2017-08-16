import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
        self.chrome_headless("/", "odoo.__DEBUG__.services['web_tour.tour'].run('event')", "odoo.__DEBUG__.services['web_tour.tour'].tours.event.ready", login='admin')
