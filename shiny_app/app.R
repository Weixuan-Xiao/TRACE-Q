library(shiny)
library(shinydashboard)
library(DT)
library(ggplot2)
library(shinyWidgets)
library(visNetwork)
library(NPCDTools)

# ==============================================================================
# 1. EMBEDDED SAMPLE DATA
# ==============================================================================

# Pre-computed GNPC diagnostic data for demo (15 students)
# Using subset of Tatsuoka1990 data with AI-generated Q-matrix (K=6)
diagnostic_demo_data <- data.frame(
  Student_ID = 1:15,
  # Pre-computed attribute patterns from GNPC
  A1 = c(1,1,0,1,1,0,1,1,1,0,1,0,1,1,0),  # Mixed to Improper
  A2 = c(1,0,1,1,0,1,0,1,1,1,0,1,1,0,1),  # Common Denominator
  A3 = c(0,1,0,1,1,0,1,0,1,0,1,1,0,1,0),  # Whole to Fraction
  A4 = c(1,1,1,0,1,1,0,1,0,1,1,0,1,1,1),  # Decompose Mixed
  A5 = c(1,1,1,1,1,1,1,1,1,1,1,1,1,1,1),  # Subtract Fractions (most mastered)
  A6 = c(1,0,1,0,1,0,1,1,0,1,0,1,0,1,0),  # Simplify
  # Sample response patterns (for display)
  Total_Correct = c(12,10,11,9,13,8,11,14,10,9,12,10,11,13,9),
  Total_Items = rep(15, 15),
  stringsAsFactors = FALSE
)

# Skill names for diagnostic report (matches skills_data)
diagnostic_skills <- data.frame(
  Skill_ID = c("A1", "A2", "A3", "A4", "A5", "A6"),
  Skill_Name = c(
    "Convert mixed to improper",
    "Find common denominator", 
    "Rewrite whole as fraction",
    "Decompose mixed numbers",
    "Subtract fractions",
    "Simplify/Reduce result"
  ),
  stringsAsFactors = FALSE
)

# Skills Definition
skills_data <- data.frame(
  Skill_ID = c("Skill01", "Skill02", "Skill03", "Skill04", "Skill05", "Skill06"),
  Description = c(
    "Convert mixed numbers to improper fractions",
    "Find common denominator",
    "Rewrite whole numbers as fractions",
    "Decompose mixed numbers",
    "Subtract fractions",
    "Simplify/Reduce result"
  ),
  stringsAsFactors = FALSE
)

# Items Data
items_data <- list(
  "Item01" = list(
    item_id = "Item01",
    stem = "$$4\\frac{3}{5} - 3\\frac{4}{10}$$",
    solver_steps = c(
      "1. Convert to improper: $$4\\frac{3}{5} = \\frac{23}{5}$$",
      "2. Simplify second term: $$3\\frac{4}{10} = 3\\frac{2}{5} = \\frac{17}{5}$$ or directly $$\\frac{34}{10}$$",
      "3. Subtract: $$\\frac{23}{5} - \\frac{17}{5} = \\frac{6}{5}$$",
      "Final Answer: $$1\\frac{1}{5}$$"
    ),
    verifier_comment = "Verified: The steps are logically sound and the calculation is correct.",
    
    # Expert Thinking (Simulated for Demo)
    expert_thinking = "Analyzing domain: Fraction Arithmetic.
1. Identification of mixed numbers suggests 'Skill01' (Mixed -> Improper) or 'Skill04' (Decomposition).
2. Different denominators (5 and 10) suggests 'Skill02' (Common Denom) or 'Skill06' (Simplify to match).
3. Subtraction operation suggests 'Skill05'.
Proposal: Check for Skill01, Skill02, Skill04, Skill05, Skill06.",
    
    # Skills proposed by Expert to look for
    expert_proposed_skills = c("Skill01", "Skill02", "Skill04", "Skill05", "Skill06"),
    
    tagger_votes = list(
      "Tagger 1" = c("Skill01", "Skill05", "Skill06"),
      "Tagger 2" = c("Skill01", "Skill02", "Skill05"), # Disagreement
      "Tagger 3" = c("Skill01", "Skill05", "Skill06"),
      "Tagger 4" = c("Skill01", "Skill05", "Skill06"),
      "Tagger 5" = c("Skill01", "Skill05", "Skill06")
    ),
    judge_rationale = "Consensus reached (4/5) for skills {Skill01, Skill05, Skill06}. Tagger 2's suggestion of Skill02 (Common Denom) was overruled as the denominator change happened via simplification, not LCM finding.",
    auditor_comment = "Flagged: The step $$\\frac{34}{10} \\rightarrow \\frac{17}{5}$$ is technically a simplification, but it serves the purpose of finding a common denominator (5). I suggest reviewing if Skill02 should also be included.",
    
    # Initial Auto-Generated Q-Vector (before human edit)
    initial_q_matrix = c(1, 0, 0, 0, 1, 1), # Skill01, Skill05, Skill06
    detected_skills = c("Skill01", "Skill05", "Skill06")
  ),
  "Item02" = list(
    item_id = "Item02",
    stem = "$$\\frac{5}{6} - \\frac{1}{9}$$",
    solver_steps = c(
      "1. Find LCM for 6 and 9: LCM is 18.",
      "2. Convert: $$\\frac{5}{6} = \\frac{15}{18}, \\frac{1}{9} = \\frac{2}{18}$$",
      "3. Subtract: $$\\frac{15}{18} - \\frac{2}{18} = \\frac{13}{18}$$",
      "Final Answer: $$\\frac{13}{18}$$"
    ),
    verifier_comment = "Verified: Correct execution of LCM and subtraction.",
    expert_thinking = "Analyzing domain: Fraction Arithmetic.
1. Proper fractions, no mixed numbers -> No Skill01/Skill04.
2. Denominators 6 and 9 are different -> Skill02 (Common Denom) required.
3. Subtraction -> Skill05.
Proposal: Check for Skill02, Skill05.",
    expert_proposed_skills = c("Skill02", "Skill05"),
    tagger_votes = list(
      "Tagger 1" = c("Skill02", "Skill05"),
      "Tagger 2" = c("Skill02", "Skill05"),
      "Tagger 3" = c("Skill02", "Skill05"),
      "Tagger 4" = c("Skill02", "Skill05"),
      "Tagger 5" = c("Skill02", "Skill05")
    ),
    judge_rationale = "Unanimous agreement (5/5). No adjudication needed.",
    auditor_comment = "Confirmed: Q-Vector [0,1,0,0,1,0] accurately reflects the solution steps.",
    initial_q_matrix = c(0, 1, 0, 0, 1, 0),
    detected_skills = c("Skill02", "Skill05")
  ),
  "Item03" = list(
    item_id = "Item03",
    stem = "$$3\\frac{4}{5} - 3\\frac{2}{5}$$",
    solver_steps = c(
      "1. Group whole numbers: $$3 - 3 = 0$$",
      "2. Group fractions: $$\\frac{4}{5} - \\frac{2}{5} = \\frac{2}{5}$$",
      "Final Answer: $$\\frac{2}{5}$$"
    ),
    verifier_comment = "Verified: Decomposition strategy is valid.",
    expert_thinking = "Analyzing domain: Mixed Number Subtraction.
1. Mixed numbers present. Steps show separation of whole and fractional parts -> Skill04 (Decomposition).
2. Denominators are same -> No Skill02 needed.
3. Subtraction -> Skill05.
Proposal: Check for Skill04, Skill05.",
    expert_proposed_skills = c("Skill04", "Skill05"),
    tagger_votes = list(
      "Tagger 1" = c("Skill04", "Skill05"),
      "Tagger 2" = c("Skill04", "Skill05"),
      "Tagger 3" = c("Skill04", "Skill05"),
      "Tagger 4" = c("Skill04", "Skill05"),
      "Tagger 5" = c("Skill04", "Skill05")
    ),
    judge_rationale = "Unanimous agreement (5/5).",
    auditor_comment = "Confirmed.",
    initial_q_matrix = c(0, 0, 0, 1, 1, 0),
    detected_skills = c("Skill04", "Skill05")
  )
)

# ==============================================================================
# 2. UI DEFINITION
# ==============================================================================

ui <- dashboardPage(
  skin = "blue",
  
  # --- Header ---
  dashboardHeader(title = "TRACE-Q"),
  
  # --- Sidebar ---
  dashboardSidebar(
    sidebarMenu(
      id = "sidebar_menu",
      menuItem("Home", tabName = "home", icon = icon("home")),
      menuItem("CDM 101", tabName = "cdm", icon = icon("book")),
      menuItem("TRACE-Q Demo", tabName = "demo", icon = icon("chart-line")),
      menuItem("Diagnostic Report", tabName = "report", icon = icon("user-check")),
      menuItem("Feedback", tabName = "feedback", icon = icon("comment"))
    )
  ),
  
  # --- Body ---
  dashboardBody(
    # Custom CSS for better styling & font size
    tags$head(
      tags$style(HTML("
        /* Narrower sidebar */
        .main-sidebar, .left-side { width: 180px; }
        .main-header .logo { width: 180px; }
        .main-header .navbar { margin-left: 180px; }
        .content-wrapper, .main-footer, .right-side { margin-left: 180px; }
        @media (max-width: 767px) {
          .content-wrapper, .main-footer, .right-side { margin-left: 0; }
        }
        
        .content-wrapper { background-color: #f4f6f9; font-size: 16px; }
        .box-header .box-title { font-size: 18px; font-weight: bold; }
        .hero-section { text-align: center; padding: 40px 20px; background: white; border-radius: 5px; margin-bottom: 20px; }
        .hero-title { font-size: 36px; font-weight: bold; color: #2c3e50; }
        .hero-subtitle { font-size: 22px; color: #7f8c8d; margin-top: 10px; }
        .step-card { background: #fff; padding: 15px; margin-bottom: 10px; border-left: 5px solid #00a65a; font-size: 15px; }
        
        /* Agent Blocks */
        .agent-block { padding: 10px; margin-bottom: 10px; border-radius: 5px; font-size: 16px; } /* Enforce font size here */
        .agent-block h5 { font-weight: bold; font-size: 18px; margin-top: 0; } /* Bold Agent Titles */
        .agent-solver { background-color: #e8f0fe; border-left: 4px solid #3c8dbc; }
        .agent-expert { background-color: #e0f7fa; border-left: 4px solid #00bcd4; }
        .agent-tagger { background-color: #f3e5f5; border-left: 4px solid #9c27b0; }
        .agent-judge { background-color: #fff3e0; border-left: 4px solid #ff9800; }
        .agent-auditor { background-color: #ffebee; border-left: 4px solid #f44336; }
        
        .highlight-skill { font-weight: bold; color: #d32f2f; background-color: #ffcdd2; padding: 2px 5px; border-radius: 3px; }
        
        .q-matrix-cell { text-align: center; font-weight: bold; padding: 10px; border: 1px solid #ddd; }
        
        /* MathJax font size adjustment */
        .mjx-chtml { font-size: 110% !important; }
      ")),
      withMathJax() # Enable MathJax
    ),
    
    tabItems(
      # --- Page 1: Home ---
      tabItem(tabName = "home",
        div(class = "hero-section",
          h1(class = "hero-title", "TRACE-Q: Transparent & Traceable AI"),
          p(class = "hero-subtitle", "Empowering practitioners to see the 'thinking' behind Cognitive Assessment"),
          br(),
          actionButton("go_to_cdm", "Get Started", class = "btn-primary btn-lg", icon = icon("arrow-circle-right"))
        ),
        fluidRow(
          valueBox("Automated", "AI instantly maps items to skills", icon = icon("magic"), color = "purple", width = 4),
          valueBox("Transparent", "See exactly why a skill was chosen", icon = icon("eye"), color = "blue", width = 4),
          valueBox("Actionable", "Better diagnosis of learning gaps", icon = icon("lightbulb"), color = "yellow", width = 4)
        )
      ),
      
      # --- Page 2: CDM 101 ---
      tabItem(tabName = "cdm",
        h2("Cognitive Diagnostic Models (CDM) 101"),
        p("Understanding the basics of how we map thinking skills."),
        
        # Row 1: What is CDM + Skill Profile Example
        fluidRow(
          column(width = 6,
            box(
              title = "1. What is Cognitive Diagnostic Modeling (CDM)?", width = NULL, status = "info", icon = icon("brain"), height = "320px",
              div(style = "font-size: 17px;",
                p("Traditional testing gives a single score (e.g., 85%), telling you ", strong("how much"), " a student knows."),
                p("CDM tells you ", strong("what"), " they know by identifying specific skill profiles."),
                tags$ul(
                  tags$li(strong("Targeted Feedback:"), " Pinpoint exactly which skills a student has mastered or missed."),
                  tags$li(strong("Timely Support:"), " Provide immediate, specific help while learning is still happening."),
                  tags$li(strong("Personalized Learning:"), " Focus instruction on individual student needs.")
                )
              )
            )
          ),
          column(width = 6,
            box(
              title = "Example: Skill Profile", width = NULL, status = "info", height = "320px",
              div(style = "font-size: 17px;",
                p("Instead of just '85%', CDM shows:", style = "margin-bottom: 10px;")
              ),
              div(style = "background: #f8f9fa; padding: 15px; border-radius: 8px; font-size: 16px;",
                tags$table(style = "width: 100%; border-collapse: collapse;",
                  tags$tr(
                    tags$th("Skill", style = "text-align: left; padding: 8px; border-bottom: 2px solid #dee2e6;"),
                    tags$th("Mastery", style = "text-align: center; padding: 8px; border-bottom: 2px solid #dee2e6;")
                  ),
                  tags$tr(tags$td("Convert mixed to improper", style = "padding: 8px;"), tags$td(icon("check", style = "color: green;"), style = "text-align: center;")),
                  tags$tr(tags$td("Find common denominator", style = "padding: 8px; background: #fff3cd;"), tags$td(icon("times", style = "color: red;"), style = "text-align: center; background: #fff3cd;")),
                  tags$tr(tags$td("Subtract fractions", style = "padding: 8px;"), tags$td(icon("check", style = "color: green;"), style = "text-align: center;")),
                  tags$tr(tags$td("Simplify result", style = "padding: 8px;"), tags$td(icon("check", style = "color: green;"), style = "text-align: center;"))
                )
              ),
              p(icon("lightbulb", style = "color: #f39c12;"), " Now teachers know: focus on ", strong("common denominator!"), style = "margin-top: 5px; font-size: 14px;")
            )
          )
        ),
        
        # Row 2: Q-Matrix + Q-Matrix Example
        fluidRow(
          column(width = 6,
            box(
              title = "2. What is a Q-Matrix?", width = NULL, status = "success", icon = icon("th"), height = "340px",
              div(style = "font-size: 17px;",
                p("The Q-Matrix bridges ", strong("questions"), " to ", strong("skills"), "."),
                p("It's a table where rows = questions, columns = skills."),
                p("Each cell: ", span("1", style = "background: #28a745; color: white; padding: 2px 8px; border-radius: 4px;"), " = required, ", 
                  span("0", style = "background: #6c757d; color: white; padding: 2px 8px; border-radius: 4px;"), " = not required."),
                hr(),
                p(strong("Traditional Q-matrix is designed by human experts, which is:")),
                tags$ul(
                  tags$li(strong("Labor-Intensive:"), " Requires significant expert time."),
                  tags$li(strong("Prone to Error:"), " Human tagging can be inconsistent."),
                  tags$li(strong("Data-Hungry:"), " Fixes often need hundreds of students.")
                )
              )
            )
          ),
          column(width = 6,
            box(
              title = "Example: Fraction Subtraction Q-Matrix", width = NULL, status = "success", height = "340px",
              div(style = "overflow-x: auto;",
                tags$table(style = "width: 100%; border-collapse: collapse; font-size: 14px; text-align: center;",
                  tags$tr(style = "background: #d4edda;",
                    tags$th("Item", style = "padding: 8px; border: 1px solid #c3e6cb;"),
                    tags$th("Mixed→Improper", style = "padding: 8px; border: 1px solid #c3e6cb;"),
                    tags$th("Common Denom", style = "padding: 8px; border: 1px solid #c3e6cb;"),
                    tags$th("Subtract", style = "padding: 8px; border: 1px solid #c3e6cb;"),
                    tags$th("Simplify", style = "padding: 8px; border: 1px solid #c3e6cb;")
                  ),
                  tags$tr(
                    tags$td(withMathJax("$$4\\frac{3}{5} - 3\\frac{4}{10}$$"), style = "padding: 8px; border: 1px solid #dee2e6; font-size: 13px;"),
                    tags$td("1", style = "padding: 8px; border: 1px solid #dee2e6; background: #28a745; color: white; font-weight: bold;"),
                    tags$td("0", style = "padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;"),
                    tags$td("1", style = "padding: 8px; border: 1px solid #dee2e6; background: #28a745; color: white; font-weight: bold;"),
                    tags$td("1", style = "padding: 8px; border: 1px solid #dee2e6; background: #28a745; color: white; font-weight: bold;")
                  ),
                  tags$tr(
                    tags$td(withMathJax("$$\\frac{5}{6} - \\frac{1}{9}$$"), style = "padding: 8px; border: 1px solid #dee2e6; font-size: 13px;"),
                    tags$td("0", style = "padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;"),
                    tags$td("1", style = "padding: 8px; border: 1px solid #dee2e6; background: #28a745; color: white; font-weight: bold;"),
                    tags$td("1", style = "padding: 8px; border: 1px solid #dee2e6; background: #28a745; color: white; font-weight: bold;"),
                    tags$td("0", style = "padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;")
                  ),
                  tags$tr(
                    tags$td(withMathJax("$$3\\frac{4}{5} - 3\\frac{2}{5}$$"), style = "padding: 8px; border: 1px solid #dee2e6; font-size: 13px;"),
                    tags$td("0", style = "padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;"),
                    tags$td("0", style = "padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;"),
                    tags$td("1", style = "padding: 8px; border: 1px solid #dee2e6; background: #28a745; color: white; font-weight: bold;"),
                    tags$td("0", style = "padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;")
                  )
                )
              ),
              p(icon("info-circle", style = "color: #17a2b8;"), " Each row shows which skills are needed for that item.", style = "margin-top: 2px; font-size: 14px;")
            )
          )
        ),
        
        # Row 3: Why TRACE-Q + Pipeline Toggle
        fluidRow(
          column(width = 6,
            box(
              title = "3. Why use TRACE-Q?", width = NULL, status = "warning", icon = icon("rocket"),
              div(style = "font-size: 17px;",
                p("TRACE-Q uses ", strong("AI agents"), " to automate Q-matrix construction with full transparency."),
                tags$ul(
                  tags$li(strong("Works Without Data:"), " Build Q-matrices purely from question text—no student data needed."),
                  tags$li(strong("Transparent & Auditable:"), " AI agents explain their reasoning for every tag."),
                  tags$li(strong("Reduces Human Effort:"), " Teachers act as final reviewers, not manual taggers."),
                  tags$li(strong("Higher Accuracy:"), " Often fits student data better than human-only versions.")
                )
              )
            )
          ),
          column(width = 6,
            box(
              title = "TRACE-Q Pipeline Plot", width = NULL, status = "warning", collapsible = TRUE, collapsed = TRUE,
              div(style = "text-align: center;",
                tags$img(src = "Pipeline.png", style = "max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);")
              )
            ),
            p(icon("cogs", style = "color: #f39c12;"), " Click the box above to view the multi-agent system architecture.", style = "font-size: 15px; margin-top: -1px;")
          )
        ),
        
        div(align = "center", style = "margin-top: 20px;", 
            actionButton("go_to_demo", "See TRACE-Q in Action", class = "btn-success btn-lg", icon = icon("chart-line")))
      ),
      
      # --- Page 3: Demo ---
      tabItem(tabName = "demo",
        h2("TRACE-Q Live Demo"),
        p("Explore the multi-agent 'thinking' process step-by-step."),
        
        # Top Control Row
        fluidRow(
          # Left Box: Item Selection & Stem
          column(width = 6,
            box(
              width = NULL, status = "primary", solidHeader = TRUE, height = "270px",
              title = "1. Select Item to Analyze",
              fluidRow(
                column(width = 5,
                  tags$div(style = "font-size: 18px; font-weight: bold; margin-bottom: 5px;", "Choose Item:"),
                  pickerInput(
                    inputId = "selected_item", label = NULL, 
                    choices = c("Item01" = "Item01", 
                                "Item02" = "Item02", 
                                "Item03" = "Item03"),
                    options = list(`style` = "btn-info"), width = "100%"
                  )
                ),
                column(width = 7,
                  tags$div(style = "font-size: 18px; font-weight: bold; margin-bottom: 5px;", "Item Stem:"),
                  div(style = "font-size: 18px; padding: 10px; text-align: center;",
                      uiOutput("item_stem_display")
                  )
                )
              )
            )
          ),
          
          # Right Box: Reference Skills
          column(width = 6,
            box(
              width = NULL, status = "info", solidHeader = TRUE, height = "270px",
              title = "2. AI-Extracted Skills for the Whole Test",
              div(style = "padding: 5px 0px 0px 0px;",
                  uiOutput("all_skills_list")
              ),
              div(align = "right", style = "margin-top: -5px;",
                  actionButton("show_full_skills_details", "View Detailed Definitions & Examples", icon = icon("book-open"), class = "btn btn-info", style = "font-size: 16px; font-weight: bold; padding: 10px 20px;")
              )
            )
          )
        ),
        
        # Process Flow
        fluidRow(
          # 3. Solution Generation
          column(width = 3,
            box(
              title = "3. Solution Generation", width = NULL, status = "primary", solidHeader = TRUE, height = "650px",
              p(style="font-size: 14px; font-style: italic; color: #666;", 
                "AI generates step-by-step solution keys."),
              div(class = "agent-block agent-solver",
                  h5(icon("robot"), "Solver Agent:"),
                  uiOutput("solver_steps_ui")
              )
            )
          ),
          
          # 4. Skill Extraction
          column(width = 3,
            box(
              title = "4. Skill Extraction", width = NULL, status = "info", solidHeader = TRUE, height = "650px",
              p(style="font-size: 14px; font-style: italic; color: #666;", 
                "Expert AI analyzes the domain to propose a list of potentially relevant skills."),
              div(class = "agent-block agent-expert",
                  h5(icon("robot"), "Expert Agent:"),
                  p("Defining relevant skills based on domain knowledge."),
                  # Collapsible thinking process
                  checkboxInput("show_expert_thinking", "Show Expert Thinking", value = FALSE),
                  conditionalPanel(
                    condition = "input.show_expert_thinking == true",
                    verbatimTextOutput("expert_thinking_display")
                  )
              ),
              hr(),
              h5("Proposed Skills for this Item:"),
              uiOutput("expert_proposed_ui")
            )
          ),
          
          # 5. Skill Annotation
          column(width = 3,
             box(
               title = "5. Skill Annotation", width = NULL, status = "warning", solidHeader = TRUE, height = "650px",
               p(style="font-size: 14px; font-style: italic; color: #666;", 
                 "Multiple AI Taggers vote on skills; a Judge AI resolves disagreements to reach consensus."),
               div(class = "agent-block agent-tagger",
                   h5(icon("robot"), "Tagger Agents (Voting):"),
                   uiOutput("tagger_votes_ui")
               ),
               div(class = "agent-block agent-judge",
                   h5(icon("robot"), "Judge Agent:"),
                   tags$b("Rationale:"),
                   uiOutput("judge_rationale"), # Changed to uiOutput for MathJax support
                   br(),
                   tags$b("Final Decided Skills:"),
                   uiOutput("judge_final_skills_ui")
               )
             )
          ),
          
          # 6. Review
          column(width = 3,
             box(
               title = "6. Review", width = NULL, status = "danger", solidHeader = TRUE, height = "650px",
               p(style="font-size: 14px; font-style: italic; color: #666;", 
                 "An Auditor AI flags potential issues, allowing teachers to finalize the Q-Matrix."),
               div(class = "agent-block agent-auditor",
                   h5(icon("robot"), "Auditor Agent:"),
                   uiOutput("auditor_comment_ui") # Use UI output to allow highlighting
               ),
               hr(),
               h5(icon("edit"), "Human Expert Review: Please modify by yourself if needed"),
               p("Modify the Q-Vector if needed:"),
               uiOutput("q_matrix_editor_ui"),
               br(),
               h5(icon("flag-checkered"), "Final Q-Matrix:"),
               uiOutput("final_q_matrix_visual_ui")
             )
          )
        ),
    # Remove bottom reference table
    # fluidRow(
    #   box(
    #     title = "Reference: All Skills Definition", width = 12, collapsible = TRUE, collapsed = TRUE,
    #     DTOutput("skills_table") 
    #   )
    # )
      ),
      
      # --- Page 4: Individual Diagnostic Report ---
      tabItem(tabName = "report",
        h2("Individual Diagnostic Report Demo", style = "font-size: 28px;"),
        p("See how CDM provides personalized skill profiles for each student using the GNPC method.", style = "font-size: 16px; margin-bottom: 20px;"),
        
        fluidRow(
          # Left Panel: Student Selection Table
          column(width = 5,
            box(
              title = "Select a Student", width = NULL, status = "primary", solidHeader = TRUE, height = "820px",
              div(style = "padding-top: 5px;",
                p("Click on a row to view the student's diagnostic report.", style = "font-size: 14px; color: #666;"),
                DTOutput("student_table"),
                br(),
                p(icon("info-circle", style = "color: #3c8dbc;"), 
                  " Attribute patterns estimated using GNPC (Non-Parametric Classification).", 
                  style = "font-size: 12px; color: #666;")
              )
            )
          ),
          
          # Right Panel: Individual Diagnostic Report
          column(width = 7,
            box(
              title = uiOutput("report_title"), width = NULL, status = "success", solidHeader = TRUE,
              uiOutput("student_report_ui")
            ),
            box(
              title = "Recommended Focus Areas", width = NULL, status = "warning", solidHeader = TRUE,
              uiOutput("focus_areas_ui")
            )
          )
        )
      ),
      
      # --- Page 5: Feedback ---
      tabItem(tabName = "feedback",
        h2("We Value Your Feedback!", style = "font-size: 32px;"),
        p("Help us improve TRACE-Q for practitioners like you.", style = "font-size: 18px; margin-bottom: 20px;"),
        
        fluidRow(
          column(width = 12,
            box(
              title = "User Feedback Survey", width = NULL, status = "primary", solidHeader = TRUE,
              div(style = "font-size: 18px;",
                p("Please share your thoughts on the usability and clarity of the TRACE-Q dashboard."),
                br(),
                
                # Personal Info (Optional)
                fluidRow(
                  column(width = 6, 
                    tags$label("Name (Optional)", style = "font-size: 18px; font-weight: bold;"),
                    textInput("fb_name", label = NULL, placeholder = "Your Name", width = "100%")
                  ),
                  column(width = 6, 
                    tags$label("Your Role", style = "font-size: 18px; font-weight: bold;"),
                    selectInput("fb_role", label = NULL, 
                                choices = c("Teacher / Instructor", "School Administrator", "Researcher / Academic", "Student", "Other"),
                                width = "100%")
                  )
                ),
                
                br(),
                # Ratings
                h4("Experience Rating", style = "font-size: 22px; font-weight: bold; margin-bottom: 20px;"),
                
                fluidRow(
                  column(width = 6,
                    tags$label("How clear was the information presented?", style = "font-size: 16px;"),
                    sliderInput("fb_rating_clarity", label = NULL, min = 1, max = 5, value = 5, ticks = TRUE, width = "100%"),
                    p("1 = Confusing, 5 = Very Clear", style = "color: #666; font-size: 14px;")
                  ),
                  column(width = 6,
                    tags$label("How useful do you find the 'traceable' AI features?", style = "font-size: 16px;"),
                    sliderInput("fb_rating_useful", label = NULL, min = 1, max = 5, value = 5, ticks = TRUE, width = "100%"),
                    p("1 = Not Useful, 5 = Very Useful", style = "color: #666; font-size: 14px;")
                  )
                ),
                
                br(),
                # Comments
                tags$label("Do you have any suggestions for improvement?", style = "font-size: 18px; font-weight: bold;"),
                textAreaInput("fb_comments", label = NULL, rows = 6, placeholder = "e.g., I would like to see...", width = "100%"),
                
                br(),
                div(align = "right",
                    actionButton("submit_feedback", "Submit Feedback", class = "btn-primary btn-lg", icon = icon("paper-plane"), style = "font-size: 18px; padding: 15px 30px;")
                )
              )
            )
          )
        )
      )
    )
  )
)

# ==============================================================================
# 3. SERVER LOGIC
# ==============================================================================

server <- function(input, output, session) {
  
  # Reactive Values to store the mutable Q-Matrix
  rv <- reactiveValues(
    current_q_vector = NULL
  )

  # Navigation Logic
  observeEvent(input$go_to_cdm, { updateTabItems(session, "sidebar_menu", "cdm") })
  observeEvent(input$go_to_demo, { updateTabItems(session, "sidebar_menu", "demo") })
  
  # Reactive Item Data
  current_item <- reactive({
    req(input$selected_item)
    items_data[[input$selected_item]]
  })
  
  # Update RV when item changes
  observeEvent(input$selected_item, {
    req(items_data[[input$selected_item]])
    rv$current_q_vector <- items_data[[input$selected_item]]$initial_q_matrix
  })
  
  # Update RV when Checkbox Group changes
  observeEvent(input$q_matrix_edit_group, {
    # input$q_matrix_edit_group returns the Skill_IDs selected (e.g. "Skill01", "Skill05")
    all_skills <- skills_data$Skill_ID
    new_vec <- rep(0, length(all_skills))
    
    # Map selected IDs back to 1s
    if (!is.null(input$q_matrix_edit_group)) {
      indices <- match(input$q_matrix_edit_group, all_skills)
      new_vec[indices] <- 1
    }
    rv$current_q_vector <- new_vec
  }, ignoreNULL = FALSE) # Allow empty selection
  
  # --- Outputs ---
  
  # Use renderUI for Item Stem to support MathJax
  output$item_stem_display <- renderUI({ 
    withMathJax(current_item()$stem)
  })
  
  output$solver_steps_ui <- renderUI({
    steps <- current_item()$solver_steps
    # Use withMathJax for each step
    tags$ul(style = "padding-left: 15px; font-size: 14px;", 
      lapply(steps, function(s) tags$li(withMathJax(s)))
    )
  })
  
  output$verifier_comment <- renderText({ current_item()$verifier_comment })
  
  output$expert_thinking_display <- renderText({ current_item()$expert_thinking })
  
  output$expert_proposed_ui <- renderUI({
    skills <- current_item()$expert_proposed_skills
    tagList(
      lapply(skills, function(s) {
        # Find description (optional, keeps it simple)
        desc <- skills_data$Description[skills_data$Skill_ID == s]
        div(style = "margin-bottom: 5px;",
            span(class = "label label-info", style = "margin-right: 0px; font-size: 15px;", s),
            span(style = "font-size: 14px;", desc)
        )
      })
    )
  })
  
  output$tagger_votes_ui <- renderUI({
    votes <- current_item()$tagger_votes
    if (is.null(votes)) return("No detailed votes available.")
    
    # Group taggers by their vote content
    vote_strings <- sapply(votes, function(x) paste(sort(x), collapse = ", "))
    unique_votes <- unique(vote_strings)
    
    tagList(
      div(style = "max-height: 200px; overflow-y: auto; font-size: 13px;",
        lapply(unique_votes, function(v_str) {
           # Find taggers who voted this way
           taggers <- names(vote_strings)[vote_strings == v_str]
           taggers_str <- paste(taggers, collapse = ", ")
           # Get individual skills for badge display
           skills_voted <- strsplit(v_str, ", ")[[1]]
           
           div(style = "margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px;",
               div(style = "font-weight: bold; color: #555;", taggers_str), 
               div(style = "padding-left: 10px; padding-top: 3px;",
                 lapply(skills_voted, function(s) {
                   span(class = "label", style = "margin-right: 3px; font-size: 11px; display: inline-block; margin-bottom: 3px; background-color: #9c27b0; color: white;", s)
                 })
               )
           )
        })
      )
    )
  })
  
  output$judge_rationale <- renderUI({ 
    # Use UI output for MathJax support in Judge rationale
    withMathJax(current_item()$judge_rationale)
  })
  
  output$judge_final_skills_ui <- renderUI({
    # Based on initial_q_matrix (which is the result of Judge before Auditor/Human review)
    q_vec <- current_item()$initial_q_matrix
    all_skills <- skills_data$Skill_ID
    selected <- all_skills[q_vec == 1]
    
    tagList(
      lapply(selected, function(s) {
        span(class = "label label-warning", style = "margin-right: 3px; font-size: 12px; display: inline-block; margin-bottom: 3px;", s)
      })
    )
  })
  
  # Auditor Comment with Highlight and MathJax
  output$auditor_comment_ui <- renderUI({
    text <- current_item()$auditor_comment
    # Simple heuristic to highlight skills in text
    text_html <- gsub("(Skill[0-9]{2})", "<span class='highlight-skill'>\\1</span>", text)
    withMathJax(HTML(text_html))
  })
  
  # Interactive Editor
  output$q_matrix_editor_ui <- renderUI({
    req(rv$current_q_vector)
    all_skills <- skills_data$Skill_ID
    # Determine currently selected based on rv$current_q_vector
    selected <- all_skills[as.logical(rv$current_q_vector)]
    
    checkboxGroupInput("q_matrix_edit_group", label = NULL,
                       choices = all_skills,
                       selected = selected,
                       inline = TRUE)
  })
  
  # Final Visual
  output$final_q_matrix_visual_ui <- renderUI({
    req(rv$current_q_vector)
    q_vec <- rv$current_q_vector
    all_skills <- skills_data$Skill_ID
    
    ui_elems <- lapply(1:length(all_skills), function(i) {
      s_id <- all_skills[i]
      val <- q_vec[i]
      color_style <- ifelse(val == 1, "background-color: #3c8dbc; color: white;", "background-color: #f4f4f4; color: #ccc;")
      div(style = "float: left; width: 15%; margin: 2px; text-align: center; border: 1px solid #ddd; border-radius: 3px;",
          div(style = paste0("padding: 2px; font-size: 10px; ", color_style), s_id),
          div(style = "font-weight: bold; font-size: 14px;", val)
      )
    })
    tagList(div(style = "overflow: hidden;", ui_elems), div(style = "clear: both;"))
  })
  
  output$all_skills_list <- renderUI({
    n_skills <- nrow(skills_data)
    tagList(
      div(
        lapply(1:n_skills, function(i) {
          s_id <- skills_data$Skill_ID[i]
          desc <- skills_data$Description[i]
          # Last skill doesn't get margin-bottom to maintain top/bottom symmetry
          mb <- if (i < n_skills) "margin-bottom: 8px;" else ""
          div(style = paste0(mb, " line-height: 1.5;"),
              span(class = "label label-primary", style = "margin-right: 8px; font-size: 16px; padding: 5px 8px;", s_id),
              span(style = "font-size: 16px;", desc)
          )
        })
      )
    )
  })

  output$skills_table <- renderDT({ 
    datatable(skills_data, options = list(dom = 't', pageLength = 10), rownames = FALSE) 
  })
  
  observeEvent(input$show_full_skills_details, {
    showModal(modalDialog(
      title = "Full Skill Definitions & Examples",
      size = "l",
      DTOutput("skills_table_modal"),
      easyClose = TRUE,
      footer = modalButton("Close")
    ))
  })
  
  output$skills_table_modal <- renderDT({
    datatable(skills_data, 
              options = list(pageLength = 10, dom = 'ft'), 
              rownames = FALSE)
  })
  
  # ===========================================================================
  # Diagnostic Report Page Logic
  # ===========================================================================
  
  # Reactive value to store selected student
  selected_student <- reactiveVal(1)
  
  # Student table with attribute patterns
  output$student_table <- renderDT({
    # Create display dataframe
    display_df <- data.frame(
      ID = diagnostic_demo_data$Student_ID,
      Pattern = apply(diagnostic_demo_data[, c("A1","A2","A3","A4","A5","A6")], 1, paste, collapse = ""),
      Score = paste0(diagnostic_demo_data$Total_Correct, "/", diagnostic_demo_data$Total_Items),
      stringsAsFactors = FALSE
    )
    
    datatable(display_df, 
              selection = "single",
              options = list(
                pageLength = 15, 
                dom = 'tp',
                columnDefs = list(list(className = 'dt-center', targets = "_all"))
              ),
              rownames = FALSE,
              colnames = c("Student", "Attribute Pattern", "Score"))
  })
  
  # Update selected student when row is clicked
  observeEvent(input$student_table_rows_selected, {
    if (!is.null(input$student_table_rows_selected)) {
      selected_student(input$student_table_rows_selected)
    }
  })
  
  # Dynamic report title
  output$report_title <- renderUI({
    paste0("Diagnostic Report: Student #", selected_student())
  })
  
  # Student diagnostic report UI
  output$student_report_ui <- renderUI({
    sid <- selected_student()
    student <- diagnostic_demo_data[sid, ]
    
    # Build skill mastery table
    skill_rows <- lapply(1:6, function(i) {
      skill_name <- diagnostic_skills$Skill_Name[i]
      mastery <- student[[paste0("A", i)]]
      mastery_icon <- if (mastery == 1) {
        icon("check-circle", style = "color: #28a745; font-size: 20px;")
      } else {
        icon("times-circle", style = "color: #dc3545; font-size: 20px;")
      }
      mastery_text <- if (mastery == 1) "Mastered" else "Not Mastered"
      bg_color <- if (mastery == 1) "#d4edda" else "#f8d7da"
      
      tags$tr(
        tags$td(paste0("A", i), style = "padding: 10px; font-weight: bold;"),
        tags$td(skill_name, style = "padding: 10px;"),
        tags$td(mastery_icon, style = paste0("padding: 10px; text-align: center; background: ", bg_color, ";")),
        tags$td(mastery_text, style = paste0("padding: 10px; text-align: center; background: ", bg_color, ";"))
      )
    })
    
    tagList(
      div(style = "margin-bottom: 15px;",
        p(icon("user", style = "color: #3c8dbc;"), 
          strong(" Student ID: "), sid,
          span(" | ", style = "color: #ccc;"),
          icon("chart-bar", style = "color: #28a745;"),
          strong(" Test Score: "), paste0(student$Total_Correct, "/", student$Total_Items, 
                                          " (", round(student$Total_Correct/student$Total_Items*100), "%)"),
          style = "font-size: 16px;")
      ),
      tags$table(style = "width: 100%; border-collapse: collapse; font-size: 15px;",
        tags$tr(style = "background: #f8f9fa; border-bottom: 2px solid #dee2e6;",
          tags$th("ID", style = "padding: 10px; text-align: left;"),
          tags$th("Skill", style = "padding: 10px; text-align: left;"),
          tags$th("Status", style = "padding: 10px; text-align: center;"),
          tags$th("", style = "padding: 10px; text-align: center;")
        ),
        skill_rows
      )
    )
  })
  
  # Focus areas (non-mastered skills)
  output$focus_areas_ui <- renderUI({
    sid <- selected_student()
    student <- diagnostic_demo_data[sid, ]
    
    # Find non-mastered skills
    non_mastered <- which(as.numeric(student[c("A1","A2","A3","A4","A5","A6")]) == 0)
    
    if (length(non_mastered) == 0) {
      tagList(
        div(style = "padding: 20px; text-align: center; background: #d4edda; border-radius: 8px;",
          icon("trophy", style = "font-size: 40px; color: #28a745;"),
          h4("Excellent! This student has mastered all skills.", style = "color: #155724; margin-top: 10px;"),
          p("Consider providing enrichment activities or advanced challenges.")
        )
      )
    } else {
      focus_items <- lapply(non_mastered, function(i) {
        skill_name <- diagnostic_skills$Skill_Name[i]
        div(style = "padding: 12px; margin-bottom: 10px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px;",
          icon("exclamation-triangle", style = "color: #856404;"),
          strong(paste0(" A", i, ": ")), skill_name,
          p(style = "margin: 5px 0 0 25px; font-size: 13px; color: #666;",
            "Suggestion: Provide targeted practice problems focusing on this skill.")
        )
      })
      
      tagList(
        p(icon("lightbulb", style = "color: #f39c12;"), 
          strong(" Recommended areas for improvement:"), 
          style = "font-size: 16px; margin-bottom: 15px;"),
        focus_items
      )
    }
  })
}

shinyApp(ui, server)