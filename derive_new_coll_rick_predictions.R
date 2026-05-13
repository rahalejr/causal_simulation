library(lme4)
library(emmeans)
library(tidyverse)
library(sysfonts)
library(showtext)
library(ragg)


resolve_existing_path <- function(paths, label) {
  hit <- paths[file.exists(paths)][1]
  if (length(hit) == 0 || is.na(hit)) {
    stop(sprintf("Could not find %s. Checked: %s", label, paste(paths, collapse = ", ")))
  }
  normalizePath(hit)
}


clamp_attribution <- function(x) {
  pmin(100, pmax(0, x))
}


project_dir <- normalizePath(getwd())

lora_regular_path <- file.path(project_dir, ".plot_fonts", "Lora-Variable.ttf")
lora_bold_path <- file.path(project_dir, ".plot_fonts", "Lora-Variable.ttf")
plot_family <- "serif"

if (file.exists(lora_regular_path) && file.exists(lora_bold_path)) {
  font_add("Lora", regular = lora_regular_path, bold = lora_bold_path)
  showtext_auto()
  plot_family <- "Lora"
}

attr_path <- resolve_existing_path(
  c(
    file.path("..", "ICK", "data", "cleaned", "causal_attr.rds"),
    "/Users/culdesac/Documents/PhD/Projects/ICK/data/cleaned/causal_attr.rds"
  ),
  "causal attribution data"
)

csm_features_path <- resolve_existing_path(
  c(
    file.path("..", "ICK", "data", "cleaned", "csm_corrected.rds"),
    "/Users/culdesac/Documents/PhD/Projects/ICK/data/cleaned/csm_corrected.rds"
  ),
  "CSM feature data"
)

rick_features_path <- resolve_existing_path(
  c(
    file.path(project_dir, "new_coll_rick_features.csv"),
    "new_coll_rick_features.csv"
  ),
  "new RICK feature csv"
)


attr_base <- readRDS(attr_path) %>%
  filter(participant != 0, rational == TRUE) %>%
  mutate(
    collision = as.integer(collision),
    order = as.integer(as.character(order)),
    num_dm = as.integer(as.character(num_dm)),
    participant_f = factor(participant),
    collision_f = factor(collision)
  )


rick_features <- read_csv(rick_features_path, show_col_types = FALSE) %>%
  mutate(
    stimulus = as.integer(stimulus),
    ball_index = as.integer(ball_index),
    order = as.integer(order),
    collision_magnitude = as.numeric(collision_magnitude),
    mapping_ease = as.numeric(mapping_ease),
    support_count = as.integer(support_count),
    support_gate = as.integer(support_gate)
  )


csm_features <- readRDS(csm_features_path) %>%
  mutate(
    stimulus = as.integer(stimulus),
    order = as.integer(as.character(order)),
    ball_index = as.integer(ball_index)
  )


m_csm_data <- attr_base %>%
  left_join(
    csm_features,
    by = c("collision" = "stimulus", "order" = "order")
  ) %>%
  mutate(
    WHETHER_g = WHETHER * DM,
    HOW_g = HOW * DM,
    SUFFICIENT_g = SUFFICIENT * DM,
    ROBUST_g = ROBUST * DM
  )


m_csm <- lmer(
  attribution ~ 1 + WHETHER_g + HOW_g + SUFFICIENT_g + ROBUST_g +
    (1 | participant_f) + (1 | collision_f),
  data = m_csm_data,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


attr_rick <- attr_base %>%
  left_join(
    rick_features,
    by = c("collision" = "stimulus", "order" = "order")
  ) %>%
  mutate(
    collision_magnitude = coalesce(collision_magnitude, 0.0),
    mapping_ease = coalesce(mapping_ease, 0.0),
    support_count = coalesce(support_count, 0L),
    support_gate = coalesce(support_gate, 0L)
  )


if (any(is.na(attr_rick$ball_index))) {
  missing_pairs <- attr_rick %>%
    filter(is.na(ball_index)) %>%
    distinct(collision, order)
  stop(
    "Missing RICK feature rows for some stimulus/order pairs:\n",
    paste(capture.output(print(missing_pairs)), collapse = "\n")
  )
}


m_rick <- lmer(
  attribution ~ 0 + support_gate + support_gate:collision_magnitude +
    support_gate:mapping_ease +
    (1 | participant_f) + (1 | collision_f),
  data = attr_rick,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


stimulus_lookup <- attr_base %>%
  distinct(collision, num_dm)

human_summary <- attr_base %>%
  group_by(collision, order) %>%
  summarise(
    human_mean = mean(attribution),
    .groups = "drop"
  )


pred_grid <- rick_features %>%
  left_join(
    stimulus_lookup,
    by = c("stimulus" = "collision")
  ) %>%
  mutate(
    participant_f = factor(levels(attr_base$participant_f)[1], levels = levels(attr_base$participant_f)),
    collision_f = factor(stimulus, levels = levels(attr_base$collision_f))
  )


pred_grid <- pred_grid %>%
  mutate(
    pred_rick = clamp_attribution(
      predict(
        m_rick,
        newdata = pred_grid,
        re.form = NA,
        allow.new.levels = TRUE
      )
    )
  )


csm_pred_grid <- csm_features %>%
  left_join(
    stimulus_lookup,
    by = c("stimulus" = "collision")
  ) %>%
  mutate(
    WHETHER_g = WHETHER * DM,
    HOW_g = HOW * DM,
    SUFFICIENT_g = SUFFICIENT * DM,
    ROBUST_g = ROBUST * DM
  )


csm_pred_grid <- csm_pred_grid %>%
  mutate(
    pred_csm = clamp_attribution(
      predict(
        m_csm,
        newdata = csm_pred_grid,
        re.form = NA,
        allow.new.levels = TRUE
      )
    )
  )


predictions <- pred_grid %>%
  left_join(
    human_summary,
    by = c("stimulus" = "collision", "order" = "order")
  ) %>%
  left_join(
    csm_pred_grid %>%
      select(stimulus, order, pred_csm),
    by = c("stimulus", "order")
  ) %>%
  select(
    stimulus,
    num_dm,
    ball_index,
    order,
    support_gate,
    support_count,
    collision_magnitude,
    mapping_ease,
    pred_rick,
    pred_csm,
    human_mean
  ) %>%
  arrange(stimulus, ball_index)


coefficient_table <- bind_rows(
  tibble(
    model = "CSM",
    term = names(fixef(m_csm)),
    estimate = unname(fixef(m_csm))
  ),
  tibble(
    model = "RICK",
    term = names(fixef(m_rick)),
    estimate = unname(fixef(m_rick))
  )
)


predictions_path <- file.path(project_dir, "new_coll_rick_predictions.csv")
coefficients_path <- file.path(project_dir, "new_coll_rick_coefficients.csv")

write_csv(predictions, predictions_path)
write_csv(coefficient_table, coefficients_path)

print(predictions)
print(coefficient_table)
message(sprintf("Predictions written to: %s", predictions_path))
message(sprintf("Coefficients written to: %s", coefficients_path))


error_long <- attr_base %>%
  left_join(
    predictions,
    by = c("collision" = "stimulus", "order" = "order")
  ) %>%
  mutate(num_dm = num_dm.x) %>%
  select(-num_dm.x, -num_dm.y) %>%
  select(participant_f, collision_f, num_dm, attribution, pred_rick, pred_csm) %>%
  pivot_longer(
    cols = c(pred_rick, pred_csm),
    names_to = "model",
    values_to = "prediction"
  ) %>%
  mutate(
    model = recode(model, pred_rick = "RICK", pred_csm = "CSM"),
    model = factor(model, levels = c("RICK", "CSM")),
    num_dm_f = factor(num_dm, levels = c(1, 2, 3)),
    abs_error = abs(attribution - prediction)
  )


mae_by_model_num_dm <- error_long %>%
  group_by(model, num_dm) %>%
  summarise(
    mae = mean(abs_error),
    sd = sd(abs_error),
    .groups = "drop"
  )


mae_by_model <- error_long %>%
  group_by(model) %>%
  summarise(
    mae = mean(abs_error),
    sd = sd(abs_error),
    .groups = "drop"
  )


m_error_num_dm <- lmer(
  abs_error ~ num_dm_f + (1 | participant_f) + (1 | collision_f),
  data = error_long,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


m_error_main <- lmer(
  abs_error ~ model + num_dm_f + (1 | participant_f) + (1 | collision_f),
  data = error_long,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


m_error_interaction <- lmer(
  abs_error ~ model * num_dm_f + (1 | participant_f) + (1 | collision_f),
  data = error_long,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


model_lrt_raw <- as.data.frame(anova(m_error_num_dm, m_error_main))
interaction_lrt_raw <- as.data.frame(anova(m_error_main, m_error_interaction))


model_fit_tests <- bind_rows(
  tibble(
    test = "model_main_effect",
    chisq = model_lrt_raw$Chisq[2],
    df = model_lrt_raw$Df[2],
    p_value = model_lrt_raw$`Pr(>Chisq)`[2]
  ),
  tibble(
    test = "model_by_num_dm_interaction",
    chisq = interaction_lrt_raw$Chisq[2],
    df = interaction_lrt_raw$Df[2],
    p_value = interaction_lrt_raw$`Pr(>Chisq)`[2]
  )
)


error_emm <- emmeans(m_error_interaction, ~ model | num_dm_f)
error_contrasts <- as.data.frame(pairs(error_emm))


mae_by_model_num_dm_path <- file.path(project_dir, "new_coll_model_fit_mae_by_condition.csv")
mae_by_model_path <- file.path(project_dir, "new_coll_model_fit_mae_overall.csv")
model_fit_tests_path <- file.path(project_dir, "new_coll_model_fit_tests.csv")
error_contrasts_path <- file.path(project_dir, "new_coll_model_fit_contrasts.csv")

write_csv(mae_by_model_num_dm, mae_by_model_num_dm_path)
write_csv(mae_by_model, mae_by_model_path)
write_csv(model_fit_tests, model_fit_tests_path)
write_csv(error_contrasts, error_contrasts_path)

print(mae_by_model_num_dm)
print(mae_by_model)
print(model_fit_tests)
print(error_contrasts)


summarise_linear_predictions <- function(data, fixed_formula, beta, vcov_beta, model_name) {
  data %>%
    group_by(num_dm, order) %>%
    group_modify(~ {
      x <- model.matrix(fixed_formula, data = .x)
      xbar <- colMeans(x)
      xbar <- matrix(xbar[names(beta)], nrow = 1)
      est <- as.numeric(xbar %*% beta)
      se <- sqrt(as.numeric(xbar %*% vcov_beta[names(beta), names(beta), drop = FALSE] %*% t(xbar)))
      tibble(
        emmean = clamp_attribution(est),
        lower.CL = clamp_attribution(est - 1.96 * se),
        upper.CL = clamp_attribution(est + 1.96 * se)
      )
    }) %>%
    ungroup() %>%
    mutate(
      ymin = lower.CL,
      ymax = upper.CL,
      model = model_name
    )
}


df_participants <- attr_base %>%
  group_by(participant_id, num_dm, order) %>%
  summarise(
    attribution_mean = mean(attribution),
    .groups = "drop"
  ) %>%
  group_by(num_dm, order) %>%
  summarise(
    emmean = mean(attribution_mean),
    sd = sd(attribution_mean),
    n_participants = n(),
    se = sd / sqrt(n_participants),
    lower.CL = emmean - 1.96 * se,
    upper.CL = emmean + 1.96 * se,
    .groups = "drop"
  ) %>%
  mutate(
    ymin = lower.CL,
    ymax = upper.CL,
    model = "Participants"
  )


rick_fixed_formula <- ~ 0 + support_gate + support_gate:collision_magnitude +
  support_gate:mapping_ease

df_rick <- pred_grid %>%
  summarise_linear_predictions(
    fixed_formula = rick_fixed_formula,
    beta = fixef(m_rick),
    vcov_beta = as.matrix(vcov(m_rick)),
    model_name = "RICK"
  )


csm_fixed_formula <- ~ 1 + WHETHER_g + HOW_g + SUFFICIENT_g + ROBUST_g

df_csm <- csm_features %>%
  left_join(
    stimulus_lookup,
    by = c("stimulus" = "collision")
  ) %>%
  mutate(
    WHETHER_g = WHETHER * DM,
    HOW_g = HOW * DM,
    SUFFICIENT_g = SUFFICIENT * DM,
    ROBUST_g = ROBUST * DM
  ) %>%
  summarise_linear_predictions(
    fixed_formula = csm_fixed_formula,
    beta = fixef(m_csm),
    vcov_beta = as.matrix(vcov(m_csm)),
    model_name = "CSM"
  )


plot_df <- bind_rows(
  df_participants,
  df_csm,
  df_rick
) %>%
  mutate(
    order = factor(order, levels = c(1, 2, 3)),
    model = factor(model, levels = c("Participants", "RICK", "CSM"))
  )


make_dm_plot <- function(dm_value) {
  dodge <- position_dodge(width = 0.60)
  guide_breaks <- c(25, 50, 75, 100)

  ggplot(
    plot_df %>% filter(num_dm == dm_value),
    aes(
      x = order,
      y = emmean,
      fill = model,
      group = model
    )
  ) +
    geom_hline(
      yintercept = guide_breaks,
      color = "#D6D6D6",
      linewidth = 0.32
    ) +
    geom_col(
      position = dodge,
      width = 0.18,
      color = "#5C5C5C",
      linewidth = 0.22
    ) +
    geom_errorbar(
      aes(ymin = ymin, ymax = ymax),
      position = dodge,
      width = 0.05,
      linewidth = 0.32,
      color = "#4A4A4A"
    ) +
    scale_x_discrete(name = "Order") +
    scale_y_continuous(
      breaks = seq(0, 100, by = 25),
      expand = expansion(mult = c(0, 0.02))
    ) +
    coord_cartesian(ylim = c(0, 100)) +
    ggtitle(sprintf("%s Difference-maker%s", dm_value, ifelse(dm_value == 1, "", "s"))) +
    ylab("Attribution") +
    theme_minimal(base_size = 11) +
    theme(
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      panel.grid.major.x = element_blank(),
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      axis.line = element_line(color = "#6A6A6A", linewidth = 0.25),
      axis.ticks = element_line(color = "#6A6A6A", linewidth = 0.25),
      legend.position = "right",
      legend.key.height = unit(0.28, "in"),
      legend.key.width = unit(0.18, "in"),
      axis.title.x = element_text(
        family = plot_family,
        size = 10.5,
        color = "#3F3F3F"
      ),
      plot.title = element_text(
        family = plot_family,
        size = 12.5,
        hjust = 0.5,
        face = "bold",
        color = "#3F3F3F"
      ),
      axis.title.y = element_text(
        family = plot_family,
        size = 10.5,
        color = "#3F3F3F"
      ),
      axis.text.x = element_text(
        family = plot_family,
        size = 9.5,
        color = "#4A4A4A"
      ),
      legend.text = element_text(
        family = plot_family,
        size = 9.5,
        color = "#4A4A4A"
      ),
      legend.title = element_text(
        family = plot_family,
        size = 10,
        color = "#3F3F3F"
      ),
      axis.text.y = element_text(
        family = plot_family,
        size = 9.5,
        color = "#4A4A4A"
      )
    ) +
    scale_fill_manual(
      name = "Model",
      values = c(
        "Participants" = "#B0B0B0",
        "RICK" = "#757575",
        "CSM" = "#2F2F2F"
      ),
      breaks = c("Participants", "RICK", "CSM")
    )
}


plot_dm1 <- make_dm_plot(1)
plot_dm2 <- make_dm_plot(2)
plot_dm3 <- make_dm_plot(3)


ggsave(
  file.path(project_dir, "new_coll_dm1_participants_csm_rick.png"),
  plot_dm1,
  width = 4.6,
  height = 3.9,
  dpi = 300,
  bg = "white",
  device = ragg::agg_png
)

ggsave(
  file.path(project_dir, "new_coll_dm2_participants_csm_rick.png"),
  plot_dm2,
  width = 4.6,
  height = 3.9,
  dpi = 300,
  bg = "white",
  device = ragg::agg_png
)

ggsave(
  file.path(project_dir, "new_coll_dm3_participants_csm_rick.png"),
  plot_dm3,
  width = 4.6,
  height = 3.9,
  dpi = 300,
  bg = "white",
  device = ragg::agg_png
)
