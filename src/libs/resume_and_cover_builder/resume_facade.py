""" This module contains the ResumeFacade class, responsible for managing interaction between the user and other components of the application. """

import hashlib
import inquirer
from pathlib import Path
from loguru import logger

from src.libs.resume_and_cover_builder.llm.llm_job_parser import LLMParser
from src.job import Job
from src.utils.chrome_utils import HTML_to_PDF
from .config import global_config


class ResumeFacade:
    def __init__(self, api_key, style_manager, resume_generator, resume_object, output_path):
        """
        Initialize the ResumeFacade with the given API key, style manager, resume generator, resume object, and output path.
        """
        lib_directory = Path(__file__).resolve().parent
        global_config.STRINGS_MODULE_RESUME_PATH = lib_directory / "resume_prompt/strings_feder-cr.py"
        global_config.STRINGS_MODULE_RESUME_JOB_DESCRIPTION_PATH = lib_directory / "resume_job_description_prompt/strings_feder-cr.py"
        global_config.STRINGS_MODULE_COVER_LETTER_JOB_DESCRIPTION_PATH = lib_directory / "cover_letter_prompt/strings_feder-cr.py"
        global_config.STRINGS_MODULE_NAME = "strings_feder_cr"
        global_config.STYLES_DIRECTORY = lib_directory / "resume_style"
        global_config.LOG_OUTPUT_FILE_PATH = output_path
        global_config.API_KEY = api_key

        self.style_manager = style_manager
        self.resume_generator = resume_generator
        self.resume_generator.set_resume_object(resume_object)
        self.selected_style = None

    def set_driver(self, driver):
        self.driver = driver

    def link_to_job(self, job_url):
        self.driver.get(job_url)
        self.driver.implicitly_wait(10)
        body_element = self.driver.find_element("tag name", "body").get_attribute("outerHTML")
        
        # Check if the job URL is from Indeed
        if "indeed.com" in job_url:
            logger.info("Processing job from Indeed")
            # Add specific parsing logic for Indeed if required

        self.llm_job_parser = LLMParser(openai_api_key=global_config.API_KEY)
        self.llm_job_parser.set_body_html(body_element)

        self.job = Job()
        self.job.role = self.llm_job_parser.extract_role()
        self.job.company = self.llm_job_parser.extract_company_name()
        self.job.description = self.llm_job_parser.extract_job_description()
        self.job.location = self.llm_job_parser.extract_location()
        self.job.link = job_url
        logger.info(f"Extracted job details from URL: {job_url}")

    def create_resume_pdf_job_tailored(self) -> tuple[bytes, str]:
        """
        Create a tailored resume PDF for the specific job description.
        """
        style_path = self.style_manager.get_style_path()
        if style_path is None:
            raise ValueError("You must choose a style before generating the PDF.")
        
        # Log a message if this is an Indeed resume
        if "indeed.com" in self.job.link:
            logger.info("Generating a resume specifically tailored for Indeed.")

        html_resume = self.resume_generator.create_resume_job_description_text(style_path, self.job.description)
        result = HTML_to_PDF(html_resume, self.driver)

        # Generate a unique file name using the job link hash
        suggested_name = hashlib.md5(self.job.link.encode()).hexdigest()[:10]
        self.driver.quit()
        return result, suggested_name

    def create_resume_pdf(self) -> tuple[bytes, str]:
        """
        Create a standard resume PDF using the selected style.
        """
        style_path = self.style_manager.get_style_path()
        if style_path is None:
            raise ValueError("You must choose a style before generating the PDF.")

        html_resume = self.resume_generator.create_resume(style_path)
        result = HTML_to_PDF(html_resume, self.driver)
        self.driver.quit()
        return result

    def create_cover_letter(self) -> tuple[bytes, str]:
        """
        Create a personalized cover letter based on the job description.
        """
        style_path = self.style_manager.get_style_path()
        if style_path is None:
            raise ValueError("You must choose a style before generating the PDF.")

        cover_letter_html = self.resume_generator.create_cover_letter_job_description(style_path, self.job.description)
        suggested_name = hashlib.md5(self.job.link.encode()).hexdigest()[:10]
        result = HTML_to_PDF(cover_letter_html, self.driver)
        self.driver.quit()
        return result, suggested_name
