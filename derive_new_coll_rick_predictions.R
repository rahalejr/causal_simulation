library(lme4)
library(emmeans)
library(tidyverse)


resolve_existing_path <- function(paths, label) {
  hit <- paths[file.exists(paths)][1]
  if (length(hit) == 0 || is.na(hit)) {
    stop(sprintf("Could not find %s. Checked: %s", label, paste(paths, collapse = ", ")))
  }
  normalizePath(hit)
}


project_dir <- normalizePath(getwd())

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
    target_alignment = as.numeric(target_alignment),
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
    target_alignment = coalesce(target_alignment, 0.0),
    mapping_ease = coalesce(mapping_ease, 0.0),
    support_count = coalesce(support_count, 0L),
    support_gate = coalesce(support_gate, 0L),
    order_numeric = order
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
  attribution ~ 0 + support_gate + support_gate:target_alignment +
    support_gate:mapping_ease + support_gate:order_numeric +
    (1 | participant_f) + (1 | collision_f),
  data = attr_rick,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


attr_human <- attr_base %>%
  mutate(
    num_dm_f = factor(num_dm, levels = c(1, 2, 3)),
    order_f = factor(order, levels = c(1, 2, 3)),
    preemption_f = factor(preemption),
    participant_id_f = factor(participant_id)
  )


m_human <- lmer(
  attribution ~ preemption_f + num_dm_f * order_f + duration + last_collision + baseline_RT +
    (1 + order_f | participant_id_f) + (1 | collision_f),
  data = attr_human,
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
    order_numeric = order,
    participant_f = factor(levels(attr_base$participant_f)[1], levels = levels(attr_base$participant_f)),
    collision_f = factor(stimulus, levels = levels(attr_base$collision_f))
  )


pred_grid <- pred_grid %>%
  mutate(
    pred_rick = predict(
      m_rick,
      newdata = pred_grid,
      re.form = NA,
      allow.new.levels = TRUE
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
    pred_csm = predict(
      m_csm,
      newdata = csm_pred_grid,
      re.form = NA,
      allow.new.levels = TRUE
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
    target_alignment,
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
        emmean = est,
        lower.CL = est - 1.96 * se,
        upper.CL = est + 1.96 * se
      )
    }) %>%
    ungroup() %>%
    mutate(
      ymin = lower.CL,
      ymax = upper.CL,
      model = model_name
    )
}


human_emm <- as.data.frame(emmeans(m_human, ~ order_f | num_dm_f))

df_participants <- human_emm %>%
  transmute(
    num_dm = as.integer(as.character(num_dm_f)),
    order = as.integer(as.character(order_f)),
    emmean,
    lower.CL,
    upper.CL,
    ymin = lower.CL,
    ymax = upper.CL,
    model = "Participants"
  )


rick_fixed_formula <- ~ 0 + support_gate + support_gate:target_alignment +
  support_gate:mapping_ease + support_gate:order_numeric

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
    model = factor(model, levels = c("Participants", "CSM", "RICK"))
  )

plot_family <- "sans"


make_dm_plot <- function(dm_value) {
  ggplot(
    plot_df %>% filter(num_dm == dm_value),
    aes(
      x = factor(order, levels = c(1, 2, 3)),
      y = emmean,
      fill = model
    )
  ) +
    geom_col(
      position = position_dodge(width = 0.8),
      width = 0.7
    ) +
    geom_errorbar(
      aes(ymin = ymin, ymax = ymax),
      width = 0.2,
      position = position_dodge(width = 0.8)
    ) +
    scale_x_discrete(name = "Order") +
    scale_y_continuous(
      limits = c(-4, 100),
      expand = c(0, 0)
    ) +
    ggtitle(sprintf("%s Difference-maker%s", dm_value, ifelse(dm_value == 1, "", "s"))) +
    ylab("Attribution") +
    theme_minimal(base_size = 14) +
    theme(
      panel.grid.minor = element_blank(),
      axis.title.x = element_text(
        family = plot_family,
        size = 12
      ),
      plot.title = element_text(
        family = plot_family,
        size = 14,
        hjust = 0.5,
        face = "bold"
      ),
      axis.title.y = element_text(
        family = plot_family,
        size = 12
      ),
      axis.text.x = element_text(
        family = plot_family,
        size = 10
      ),
      legend.text  = element_text(
        family = plot_family,
        size = 10
      ),
      legend.title  = element_text(
        family = plot_family,
        size = 10
      ),
      axis.text.y = element_text(
        family = plot_family,
        size = 10
      )
    ) +
    scale_fill_manual(
      name = "Model",
      values = c(
        "Participants" = "dodgerblue3",
        "CSM" = "firebrick2",
        "RICK" = "darkolivegreen3"
      )
    )
}


plot_dm1 <- make_dm_plot(1)
plot_dm2 <- make_dm_plot(2)
plot_dm3 <- make_dm_plot(3)


ggsave(
  file.path(project_dir, "new_coll_dm1_participants_csm_rick.png"),
  plot_dm1,
  width = 7,
  height = 5,
  dpi = 300
)

ggsave(
  file.path(project_dir, "new_coll_dm2_participants_csm_rick.png"),
  plot_dm2,
  width = 7,
  height = 5,
  dpi = 300
)

ggsave(
  file.path(project_dir, "new_coll_dm3_participants_csm_rick.png"),
  plot_dm3,
  width = 7,
  height = 5,
  dpi = 300
)
