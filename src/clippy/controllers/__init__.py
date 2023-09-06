from clippy.controllers.controller import Controller
from clippy.controllers.apis.cohere_controller import CohereController

# To Add Additional Controllers They should replicate the CohereController
Controller.Clients.Cohere = CohereController
