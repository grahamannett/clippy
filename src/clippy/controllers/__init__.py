from clippy.controllers.controller import Controller
from clippy.controllers.apis.cohere_controller import CohereController, Responses
from clippy.controllers.apis.cohere_controller_utils import Embeddings, Generation, Generations
from clippy.controllers.utils import allow_full_response, truncate_left, find_json_response, is_truncated, build_stack

# To Add Additional Controllers They should replicate the CohereController
Controller.Clients.Cohere = CohereController
