import os

import cv2
from playwright.async_api import Page
from clippy.dm.data_manager import DataManager

from clippy.states import Action


class ScreenshotMatcher:
    def __init__(self, data_manager: DataManager) -> None:
        self.data_manager = data_manager
        self.data_dir = "data/tmp/screenshots"

    def get_latest_screenshot_path(self, data_dir, task_id, step_id):
        screenshot_path = f"{data_dir}/{task_id}/{step_id}.png"
        return screenshot_path

    def get_action_template(self, action: Action, screenshot_path: str = None):
        """this gets the subimage in the original screenshot that the action is referring to"""
        action_bounding_box = action.bounding_box

        if not os.path.exists(screenshot_path):
            breakpoint()

        screenshot = cv2.imread(screenshot_path)
        action_template_outfile = f"{self.data_dir}/action_template.png"
        extra_buffer = 20
        x, y, w, h = action_bounding_box.x, action_bounding_box.y, action_bounding_box.width, action_bounding_box.height
        scroll_x, scroll_y = action_bounding_box.scrollX, action_bounding_box.scrollY
        x1, x2 = x + scroll_x - extra_buffer, x + scroll_x + w + extra_buffer
        y1, y2 = y + scroll_y - extra_buffer, y + scroll_y + h + extra_buffer

        x1, x2, y1, y2 = int(x1), int(x2), int(y1), int(y2)
        # cv2.rectangle(screenshot, (x1, y1), (x2, y2), (0, 255, 0), 2)
        template = screenshot[y1:y2, x1:x2]
        cv2.imwrite(action_template_outfile, template)
        self.action_template_outfile = action_template_outfile
        return action_template_outfile

    def get_point_from_template(self, page: Page):
        curr_step_screenshot = f"{self.data_dir}/curr_step_screenshot.png"
        # TODO: if this works, try to get the image from buffer instea

        viewport_size = page.viewport_size
        num_pages = 5
        screenshot = page.screenshot(
            path=curr_step_screenshot,
            full_page=True,
            clip={
                "x": 0,
                "y": 0,
                "width": viewport_size["width"],
                "height": viewport_size["height"] * num_pages,
            },
        )
        screenshot = cv2.imread(curr_step_screenshot)

        template = cv2.imread(self.action_template_outfile)

        imageGray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        templateGray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        result = cv2.matchTemplate(imageGray, templateGray, cv2.TM_CCOEFF_NORMED)
        (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(result)

        (startX, startY) = maxLoc
        endX = startX + template.shape[1]
        endY = startY + template.shape[0]

        middle_point = (startX + endX) // 2, (startY + endY) // 2

        cv2.rectangle(screenshot, (startX, startY), (endX, endY), (255, 0, 0), 3)
        cv2.circle(screenshot, middle_point, 10, (0, 0, 255), -1)
        cv2.imwrite(f"{self.data_dir}/curr_step_point.png", screenshot)
        return middle_point
