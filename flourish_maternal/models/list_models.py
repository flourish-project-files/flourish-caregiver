from edc_base.model_mixins import BaseUuidModel, ListModelMixin


class ChronicConditions(ListModelMixin, BaseUuidModel):
    pass


class CaregiverMedications(ListModelMixin, BaseUuidModel):
    pass


class WcsDxAdult(ListModelMixin, BaseUuidModel):
    pass
