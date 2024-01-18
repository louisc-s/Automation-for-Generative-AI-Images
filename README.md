# Automation-for-Generative-AI-Images
Code to automate the production of generative images from a large diffusion model using pre-made prompts

## Overview

This code automates the production of generative images from a large commercial diffusion model. The program loads pre-made prompts from a CSV file and enters these into the models UI to generate the images. The program then proceeds to upscales all generated images and downloads them into a folder. The program is able to track which prompts have been utilised and starts from first unused prompt when it is next run.  

## Project Structure 

1. automation.py - python code to automate image generation 
  
2. start_point.txt -  text file used to track prompts 
   
3. prompts.csv - csv file containing prompts to be used (not included in repository)
   
4. crednetials.txt - text file containing username and passsword for logging into commercial diffusion model (not included in repository)

## Author 

Louis Chapo-Saunders
