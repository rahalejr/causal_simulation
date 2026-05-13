library(lme4)
library(emmeans)
library(tidyverse)
library(sysfonts)
library(showtext)
library(ragg)
library(png)
library(grid)


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

plot_family <- "sans"
lora_path <- file.path(project_dir, ".plot_fonts", "Lora-Variable.ttf")
if (file.exists(lora_path)) {
  font_add("LoraPlot", regular = lora_path, bold = lora_path)
  showtext_auto()
  plot_family <- "LoraPlot"
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


m_rick <- lmer(
  attribution ~ 0 + support_gate + support_gate:collision_magnitude +
    support_gate:mapping_ease + (1 | participant_f) + (1 | collision_f),
  data = attr_rick,
  REML = FALSE,
  control = lmerControl(optimizer = "bobyqa")
)


stimulus_lookup <- attr_base %>%
  distinct(collision, num_dm)


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
        ymin = clamp_attribution(est - 1.96 * se),
        ymax = clamp_attribution(est + 1.96 * se)
      )
    }) %>%
    ungroup() %>%
    mutate(model = model_name)
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
    n = n(),
    se = sd / sqrt(n),
    ymin = emmean - 1.96 * se,
    ymax = emmean + 1.96 * se,
    .groups = "drop"
  ) %>%
  mutate(model = "Participants")


rick_fixed_formula <- ~ 0 + support_gate + support_gate:collision_magnitude +
  support_gate:mapping_ease

df_rick <- rick_features %>%
  left_join(
    stimulus_lookup,
    by = c("stimulus" = "collision")
  ) %>%
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


plot_df <- bind_rows(df_participants, df_rick, df_csm) %>%
  mutate(
    num_dm = as.integer(num_dm),
    order = factor(order, levels = c(1, 2, 3)),
    model = factor(model, levels = c("Participants", "RICK", "CSM"))
  )


make_dm_plot <- function(dm_value) {
  dodge <- position_dodge(width = 0.72)
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
      width = 0.24,
      color = "#5C5C5C",
      linewidth = 0.22
    ) +
    geom_errorbar(
      aes(ymin = ymin, ymax = ymax),
      position = dodge,
      width = 0.06,
      linewidth = 0.32,
      color = "#4A4A4A"
    ) +
    scale_fill_manual(
      name = "Model",
      values = c(
        "Participants" = "#B0B0B0",
        "RICK" = "#757575",
        "CSM" = "#2F2F2F"
      ),
      breaks = c("Participants", "RICK", "CSM")
    ) +
    scale_x_discrete(name = "Order") +
    scale_y_continuous(
      breaks = c(0, 25, 50, 75, 100),
      expand = expansion(mult = c(0, 0.02))
    ) +
    coord_cartesian(ylim = c(0, 100)) +
    ggtitle(sprintf("%s Difference-maker%s", dm_value, ifelse(dm_value == 1, "", "s"))) +
    ylab("Attribution") +
    theme_minimal(base_size = 14) +
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
        size = 13,
        color = "#3F3F3F"
      ),
      plot.title = element_text(
        family = plot_family,
        size = 16,
        hjust = 0.5,
        face = "bold",
        color = "#3F3F3F"
      ),
      axis.title.y = element_text(
        family = plot_family,
        size = 13,
        color = "#3F3F3F"
      ),
      axis.text.x = element_text(
        family = plot_family,
        size = 12,
        color = "#4A4A4A"
      ),
      legend.text = element_text(
        family = plot_family,
        size = 12,
        color = "#4A4A4A"
      ),
      legend.title = element_text(
        family = plot_family,
        size = 12.5,
        color = "#3F3F3F"
      ),
      axis.text.y = element_text(
        family = plot_family,
        size = 12,
        color = "#4A4A4A"
      )
    )
}


plot_dm1 <- make_dm_plot(1)
plot_dm2 <- make_dm_plot(2)
plot_dm3 <- make_dm_plot(3)

plots <- list(
  dm1 = plot_dm1,
  dm2 = plot_dm2,
  dm3 = plot_dm3
)


render_plot_to_temp_png <- function(plot_obj, width = 7.0, height = 5.2, dpi = 300) {
  out_path <- tempfile(fileext = ".png")
  ggsave(
    out_path,
    plot_obj,
    width = width,
    height = height,
    dpi = dpi,
    bg = "white",
    device = ragg::agg_png
  )
  out_path
}


preview_png <- function(path) {
  if (!interactive()) {
    return(invisible(NULL))
  }

  if (dev.cur() == 1) {
    try(dev.new(width = 7.0, height = 5.2), silent = TRUE)
  }

  img <- png::readPNG(path)
  grid::grid.newpage()
  grid::grid.raster(img, interpolate = FALSE)
  invisible(NULL)
}


if (interactive()) {
  preview_png(render_plot_to_temp_png(plot_dm1))
  preview_png(render_plot_to_temp_png(plot_dm2))
  preview_png(render_plot_to_temp_png(plot_dm3))
} else {
  message("Plots loaded into `plots`; source this file from an interactive R session to print them.")
}
